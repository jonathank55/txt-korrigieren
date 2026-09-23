#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
duden_orthography_engine.py - Deterministische Duden- & Amtliches Regelwerk Orthographie-Engine.
Hochoptimierte Fassung mit mehrstufigem Caching (In-Memory O(1), SQLite O(1), Negativ-Cache, Timeout-Guard).
"""

import warnings
warnings.filterwarnings("ignore")
import sys
import os
import json
import sqlite3
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

# Standalone Datenverzeichnis für SQLite-Cache (XDG-Standard, autark)
if os.path.exists(os.path.expanduser("~/.gemini/config/data")):
    DATA_DIR = os.path.expanduser("~/.gemini/config/data")
else:
    DATA_DIR = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share/txt-korrigieren"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "duden_cache.sqlite")

OFFICIAL_RULES_INDEX = {
    "ss_sz": {
        "paragraph": "§ 25",
        "title": "Schreibung von s, ss und ß",
        "summary": "Nach kurzem Vokal 'ss', nach langem Vokal oder Diphthong 'ß' (Maß, Straße, groß). Bei Versalien 'ß' beibehalten."
    },
    "substantivierung": {
        "paragraph": "§ 57 / § 58",
        "title": "Groß- und Kleinschreibung von Substantivierungen",
        "summary": "Substantivierte Adjektive und Partizipien groß. Zahladjektive ('wenige', 'viele', 'einige') in der Regel klein (§ 58)."
    },
    "getrennt_zusammen": {
        "paragraph": "§ 33 - § 39",
        "title": "Getrennt- und Zusammenschreibung",
        "summary": "'zugrunde liegen' / 'zugrundeliegenden' beide zulässig (§ 39); 'lang anhaltend' empfohlen (§ 36)."
    },
    "bindestrich": {
        "paragraph": "§ 59 - § 66",
        "title": "Schreibung mit Bindestrich",
        "summary": "Layout-Trennstriche im Fließtext unzulässig."
    },
    "kommasetzung": {
        "paragraph": "§ 71 - § 78",
        "title": "Zeichensetzung bei Nebensätzen und Infinitivgruppen",
        "summary": "Nebensätze und satzwertige Infinitivgruppen mit 'um zu', 'ohne zu' erfordern Kommas."
    },
    "silbentrennung": {
        "paragraph": "§ 107 - § 115",
        "title": "Worttrennung am Zeilenende",
        "summary": "Mehrsilbige Wörter nach Sprechsilben trennen."
    },
    "pronominalreferenz_reflexiv": {
        "paragraph": "Duden-Grammatik § 484 ff.",
        "title": "Rückbezügliche Pronominalreferenz",
        "summary": "Rückbezug auf das Subjekt verlangt Possessivpronomen 'sein/ihr', schließt Demonstrativpronomen 'dessen/deren' aus."
    },
    "deklination_nach_determinantien": {
        "paragraph": "Duden-Grammatik § 1515",
        "title": "Adjektivdeklination nach alle/sämtliche/beide",
        "summary": "Nach 'alle', 'sämtliche' und 'beide' folgt im Plural ausnahmslos die schwache Endung '-en' (z. B. 'sämtliche humanitären Probleme')."
    },
    "indefinitpronomen_genus": {
        "paragraph": "Duden-Grammatik § 491",
        "title": "Genus- und Kasuskongruenz bei Indefinitpronomina",
        "summary": "Im Akkusativ Neutrum Singular lautet das selbständige Indefinitpronomen 'eines' (z. B. 'eines von vielen Beispielen', nicht maskulin 'einen')."
    },
    "gedankenstrich_abstand": {
        "paragraph": "DIN 5008 / Duden Wörterbuch der sprachlichen Zweifelsfälle",
        "title": "Abstand beim Gedankenstrich",
        "summary": "Vor und nach dem Gedankenstrich steht im standarddeutschen Schriftsatz stets ein Leerzeichen."
    }
}

KNOWN_COMMON_ERRORS = {
    "wiederrum": {
        "correct": "wiederum",
        "explanation": "Duden: Das Adverb heißt 'wiederum' (mit einfachem r).",
        "rule": "Laut-Buchstaben-Zuordnung"
    },
    "naturunfall": {
        "correct": "Naturereignis / Naturkatastrophe",
        "explanation": "Duden: 'Naturunfall' existiert nicht. Normgerecht: 'Naturereignis' oder 'höhere Gewalt'.",
        "rule": "Lexik & Wortbildung"
    }
}

# Lokaler Memory-Cache für Sub-Millisekunden-Zugriffe
_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
_NEGATIVE_CACHE: Set[str] = set()
_DB_INITIALIZED: bool = False

# Hochfrequente deutsche Grundwörter (Vermeidung von unnötigen Disk-/Netzwerk-Abfragen)
COMMON_GERMAN_WORDS: Set[str] = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines", "einem", "einen",
    "und", "oder", "aber", "denn", "doch", "da", "weil", "wenn", "als", "wie", "ob", "so", "dass", "daß",
    "zu", "von", "mit", "nach", "bei", "aus", "vor", "über", "unter", "zwischen", "an", "auf", "in", "durch", "für", "um", "gegen", "ohne", "wider",
    "sich", "er", "sie", "es", "wir", "ihr", "man", "wer", "was", "wo", "wann", "warum", "weshalb",
    "welche", "welcher", "welches", "welchem", "welchen", "jener", "jene", "jenes", "jenem", "jenen",
    "dieser", "diese", "dieses", "diesem", "diesen", "mein", "dein", "sein", "unser", "euer",
    "nicht", "noch", "schon", "nur", "auch", "sehr", "mehr", "immer", "wieder", "hier", "dort", "nun", "jetzt", "bereits", "heute", "gestern", "morgen",
    "ist", "sind", "war", "waren", "gewesen", "wird", "werden", "wurde", "wurden", "worden", "hat", "haben", "hatte", "hatten", "gehabt",
    "kann", "können", "konnte", "konnten", "muss", "müssen", "musste", "mussten", "soll", "sollen", "sollte", "sollten",
    "will", "wollen", "wollte", "wollten", "darf", "dürfen", "durfte", "durften", "lässt", "lassen", "ließ", "ließen",
    "viel", "viele", "vielen", "vieler", "wenig", "wenige", "wenigen", "weniger", "einige", "einigen", "alle", "allen", "aller", "beide", "beiden",
    "etwas", "nichts", "jemand", "niemand", "selbst", "einander", "voneinander", "miteinander", "untereinander",
    "des weiteren", "des weiteren", "gleichwohl", "folglich", "schließlich", "dennoch", "somit", "mithin",
    "jahr", "jahre", "jahren", "monat", "monate", "monaten", "tag", "tage", "tagen", "zeit", "zeiten", "mensch", "menschen", "leben", "lebens"
}

def init_db():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS duden_words (
                word TEXT PRIMARY KEY,
                title TEXT,
                part_of_speech TEXT,
                frequency INTEGER,
                word_separation TEXT,
                meaning_overview TEXT,
                synonyms TEXT,
                inflection TEXT,
                alternative_spellings TEXT,
                raw_data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS duden_not_found (
                word TEXT PRIMARY KEY,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_duden_words_word ON duden_words(word)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_duden_not_found_word ON duden_not_found(word)")
        conn.commit()
        conn.close()
        _DB_INITIALIZED = True
    except Exception as e:
        sys.stderr.write(f"[DUDEN_DB_INIT_ERROR] {e}\n")

def get_cached_word(word: str) -> Optional[Dict[str, Any]]:
    norm = word.strip().lower()
    
    # 1. Schneller Memory-Cache
    if norm in _MEMORY_CACHE:
        return _MEMORY_CACHE[norm]
    if norm in _NEGATIVE_CACHE:
        return None

    # 2. SQLite-Cache
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM duden_words WHERE word = ?", (norm,))
        row = cur.fetchone()
        
        if row:
            entry = {
                "word": row["word"],
                "title": row["title"],
                "part_of_speech": row["part_of_speech"],
                "frequency": row["frequency"],
                "word_separation": row["word_separation"],
                "meaning_overview": row["meaning_overview"],
                "synonyms": json.loads(row["synonyms"] or "[]"),
                "inflection": json.loads(row["inflection"] or "{}"),
                "alternative_spellings": json.loads(row["alternative_spellings"] or "[]"),
                "source": "sqlite_cache",
                "cached_at": row["updated_at"]
            }
            conn.close()
            _MEMORY_CACHE[norm] = entry
            return entry

        # Negativ-Cache in SQLite prüfen
        cur.execute("SELECT word FROM duden_not_found WHERE word = ?", (norm,))
        if cur.fetchone():
            _NEGATIVE_CACHE.add(norm)
            conn.close()
            return None

        conn.close()
    except Exception:
        pass
    return None

def save_word_to_cache(entry: Dict[str, Any]):
    norm = entry["word"].strip().lower()
    _MEMORY_CACHE[norm] = entry
    _NEGATIVE_CACHE.discard(norm)

    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Typsichere Aufbereitung aller Felder (Verhindert Binding Parameter Fehler)
        word_sep = entry.get("word_separation", "")
        if isinstance(word_sep, list):
            word_sep = "|".join(str(x) for x in word_sep)
        elif not isinstance(word_sep, str):
            word_sep = str(word_sep or "")

        freq = entry.get("frequency", 0)
        if isinstance(freq, int):
            freq_val = freq
        elif isinstance(freq, str) and freq.isdigit():
            freq_val = int(freq)
        else:
            freq_val = 0

        title_val = str(entry.get("title") or "")
        pos_val = str(entry.get("part_of_speech") or "")
        meaning_val = str(entry.get("meaning_overview") or "")
        syns_val = json.dumps(entry.get("synonyms") or [], ensure_ascii=False)
        infl_val = json.dumps(entry.get("inflection") or {}, ensure_ascii=False)
        alt_val = json.dumps(entry.get("alternative_spellings") or [], ensure_ascii=False)
        raw_val = json.dumps(entry.get("raw_data") or {}, ensure_ascii=False)

        cur.execute("""
            INSERT OR REPLACE INTO duden_words 
            (word, title, part_of_speech, frequency, word_separation, meaning_overview, synonyms, inflection, alternative_spellings, raw_data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            norm,
            title_val,
            pos_val,
            freq_val,
            word_sep,
            meaning_val,
            syns_val,
            infl_val,
            alt_val,
            raw_val
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        sys.stderr.write(f"[DUDEN_CACHE_ERROR] {e}\n")

def save_not_found(word: str):
    norm = word.strip().lower()
    _NEGATIVE_CACHE.add(norm)
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO duden_not_found (word, checked_at) VALUES (?, CURRENT_TIMESTAMP)", (norm,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def fetch_from_duden_online(word: str, timeout: float = 3.5) -> Optional[Dict[str, Any]]:
    norm = word.strip().lower()
    try:
        import duden
        d_word = None
        
        # Ausführung mit Timeout-Schutz via ThreadPool
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(duden.get, word.strip())
            try:
                d_word = future.result(timeout=timeout)
            except Exception:
                d_word = None

        if not d_word:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(duden.search, word.strip())
                try:
                    s_results = future.result(timeout=timeout)
                    if s_results:
                        d_word = s_results[0]
                except Exception:
                    d_word = None

        if not d_word:
            save_not_found(norm)
            return None
            
        entry = {
            "word": norm,
            "title": getattr(d_word, "title", word),
            "part_of_speech": getattr(d_word, "part_of_speech", ""),
            "frequency": getattr(d_word, "frequency", 0),
            "word_separation": getattr(d_word, "word_separation", ""),
            "meaning_overview": str(getattr(d_word, "meaning_overview", "")),
            "synonyms": getattr(d_word, "synonyms", []) or [],
            "alternative_spellings": getattr(d_word, "alternative_spellings", []) or [],
            "inflection": {},
            "source": "duden_online"
        }
        save_word_to_cache(entry)
        return entry
    except Exception:
        save_not_found(norm)
        return None

def lookup(word: str, allow_online: bool = True) -> Dict[str, Any]:
    norm = word.strip().lower()
    
    # 0. Bekannte Fehler direkt deterministisch abfangen
    if norm in KNOWN_COMMON_ERRORS:
        err = KNOWN_COMMON_ERRORS[norm]
        return {
            "status": "error_identified",
            "query": word,
            "error_analysis": err,
            "duden_reference": f"Duden-Korrektur: '{word}' ist fehlerhaft; normgerecht ist '{err['correct']}'."
        }

    # 1. Deutsche Grundwörter (Sub-Mikrosekunden O(1) Treffer)
    if norm in COMMON_GERMAN_WORDS:
        return {
            "status": "ok",
            "entry": {
                "word": norm,
                "title": word,
                "part_of_speech": "Standardvokabular",
                "source": "common_lexicon"
            },
            "source": "common_lexicon"
        }

    # 2. Lokaler Cache (Memory & SQLite)
    cached = get_cached_word(norm)
    if cached:
        return {"status": "ok", "entry": cached, "source": "local_sqlite_cache"}

    # 3. Negativ-Cache
    if norm in _NEGATIVE_CACHE:
        return {
            "status": "not_found",
            "query": word,
            "message": f"Wort '{word}' nicht im Duden verzeichnet (gecacht)."
        }

    # 4. Optionaler Online-Abgleich
    if allow_online:
        fetched = fetch_from_duden_online(word)
        if fetched:
            return {"status": "ok", "entry": fetched, "source": "duden_live_fetch"}

    return {
        "status": "not_found",
        "query": word,
        "message": f"Wort '{word}' nicht direkt im Duden verzeichnet."
    }

def lookup_batch(words: List[str], allow_online: bool = False) -> Dict[str, Dict[str, Any]]:
    """Prüft eine Liste von Wörtern extrem effizient im Batch."""
    results = {}
    missing_words = []

    for w in words:
        norm = w.strip().lower()
        if not norm or len(norm) < 2:
            continue
        if norm in KNOWN_COMMON_ERRORS or norm in COMMON_GERMAN_WORDS or norm in _MEMORY_CACHE or norm in _NEGATIVE_CACHE:
            results[w] = lookup(w, allow_online=False)
        else:
            missing_words.append(w)

    if missing_words:
        init_db()
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # SQLite In-Abfrage in Batches zu 200
            for i in range(0, len(missing_words), 200):
                batch = missing_words[i:i+200]
                placeholders = ",".join("?" for _ in batch)
                cur.execute(f"SELECT * FROM duden_words WHERE word IN ({placeholders})", [b.strip().lower() for b in batch])
                for row in cur.fetchall():
                    w_norm = row["word"]
                    entry = {
                        "word": w_norm,
                        "title": row["title"],
                        "part_of_speech": row["part_of_speech"],
                        "frequency": row["frequency"],
                        "source": "sqlite_cache"
                    }
                    _MEMORY_CACHE[w_norm] = entry

                # Not-found abfragen
                cur.execute(f"SELECT word FROM duden_not_found WHERE word IN ({placeholders})", [b.strip().lower() for b in batch])
                for row in cur.fetchall():
                    _NEGATIVE_CACHE.add(row["word"])
            conn.close()
        except Exception:
            pass

        # Zweiter Durchlauf
        for w in missing_words:
            results[w] = lookup(w, allow_online=allow_online)

    return results

def update_duden_subsystem() -> Dict[str, Any]:
    init_db()
    res = {
        "timestamp": datetime.now().isoformat(),
        "pip_update": False,
        "db_integrity": False,
        "cached_words_count": 0,
        "official_rules_count": len(OFFICIAL_RULES_INDEX)
    }

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "duden"],
            capture_output=True, text=True, timeout=60
        )
        res["pip_update"] = (proc.returncode == 0)
        res["pip_output"] = proc.stdout.strip().split("\n")[-1] if proc.stdout else ""
    except Exception as e:
        res["pip_error"] = str(e)

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        check = cur.fetchone()
        res["db_integrity"] = (check[0] == "ok") if check else False
        
        cur.execute("SELECT COUNT(*) FROM duden_words")
        res["cached_words_count"] = cur.fetchone()[0]
        
        cur.execute("VACUUM")
        conn.commit()
        conn.close()
    except Exception as e:
        res["db_error"] = str(e)

    return res

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Verwendung: duden_orthography_engine.py lookup <Wort> | update")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "lookup" and len(sys.argv) > 2:
        res = lookup(sys.argv[2])
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif cmd in ("update", "--update", "maintenance"):
        res = update_duden_subsystem()
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"Unbekannter Befehl: {cmd}")
        sys.exit(1)
