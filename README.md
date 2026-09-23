# txt-korrigieren

**Deterministische Text-, Orthografie- und Stilkorrektur-Engine für die Kommandozeile.**

Ein hochpräzises, maximal konservatives Werkzeug zur automatisierten Korrektur von Text-, Word-, PDF-, Typst- und RTF-Dokumenten nach den amtlichen Regeln der deutschen Rechtschreibung und den Vorgaben des Dudens. Verfügt über einen dedizierten Schalter zur Optimierung von Stil und Idiomatik (`-s`).

---

## Funktionen & Besonderheiten

- **Maximal konservativer Berichtigungsstandard (Standardmodus):** Der Tonfall, Rhythmus und Satzbau des Autors bleiben unberührt. Korrekturen beschränken sich streng auf unstreitige Orthografie-, Grammatik- und Interpunktionsfehler (Zero Style-Tampering).
- **Stil- & Idiomatik-Modus (`-s`):** Beseitigt gezielt unidiomatische Wendungen (z. B. *Sinn machen*, *in keinster Weise*), bürokratischen Nominalstil (*im Hinblick auf die Tatsache, dass*), Pleonasmen (*bereits schon*, *voll und ganz*) sowie schiefe Kollokationen.
- **Multiformat-Unterstützung:** Verarbeitet `.txt`, `.md`, `.docx` (unter Erhalt aller Word-Styles und Drop Caps), `.pdf` (visuelle In-situ-Korrektur und Redaction via PyMuPDF), `.typ` (Typst) sowie `.rtf` und macOS `.rtfd`-Pakete (unter Beachtung aller RTF-Escape-Sequenzen).
- **In-situ-Disziplin & automatische Sicherung:** Korrigiert Dokumente direkt am Ursprungsort. Vor jeder Schreiboperation wird automatisch eine atomare Sicherheitskopie angelegt.
- **Blitzschnelle Ausführung:** Vollständige Korrektur in wenigen Millisekunden (< 50 ms) durch lokale Regex-Heuristiken und mehrstufiges Caching.

---

## Installation

### Einzeiler via Terminal

```bash
curl -fsSL https://raw.githubusercontent.com/jonathank55/txt-korrigieren/main/install.sh | bash
```

### Manuelle Installation

1. **Repository klonen:**
   ```bash
   git clone https://github.com/jonathank55/txt-korrigieren.git
   cd txt-korrigieren
   ```

2. **Installationsskript ausführen:**
   ```bash
   ./install.sh
   ```

---

## Verwendung

```bash
txt-korrigieren DATEI [OPTIONEN]
```

### Optionen

| Option | Parameter | Funktion |
| :--- | :--- | :--- |
| `-s` | `STIL` | **Stil- & Idiomatikkorrektur:** Optimiert Floskeln, Pleonasmen und Nominalstil (`all`, `floskeln`, `pleonasmen`, `nominalstil`; Standard bei `-s`: `all`). |
| `-a` | `MODUS` | **Prüflauf (Audit):** Reine Fehleranalyse ohne Schreibzugriff (`detail` für Vollbericht, `summary` für Kurzüberblick; Standard bei `-a`: `detail`). |
| `-o` | `AUSGABE` | **Ausgabepfad:** Schreibt den bereinigten Text zusätzlich in den angegebenen Zieldateipfad (.txt). |
| `-j` | `FORMAT` | **JSON-Ausgabe:** Maschinelles JSON für Pipelines (`pretty` formatiert, `compact` einzeilig; Standard bei `-j`: `pretty`). |
| `-h` | – | **Hilfe:** Zeigt die einzeilige Befehlshilfe an. |

---

## Anwendungsbeispiele

### 1. Reine Rechtschreib- und Grammatikprüfung (Trockenlauf)
```bash
txt-korrigieren -a Dokument.md
```

### 2. Normative In-situ-Korrektur (Rechtschreibung & Grammatik)
```bash
txt-korrigieren Manuskript.docx
```

### 3. Stil- & Idiomatikkorrektur mit Überarbeitung
```bash
txt-korrigieren -s Aufsatz.rtfd
```

### 4. PDF-Dokument prüfen und korrigieren
```bash
txt-korrigieren Dokument.pdf
```

---

## Unterstützte Dateiformate

- **PDF-Dokumente:** `.pdf` (visuelle In-situ-Korrektur mit Schriftarten- und Baseline-Anpassung via PyMuPDF)
- **Markdown & Plaintext:** `.txt`, `.md`
- **Microsoft Word:** `.docx` (Run-by-Run-Modifikation ohne Zerstörung von Formatvorlagen)
- **Typst-Dokumente:** `.typ`
- **Rich Text Format:** `.rtf` sowie macOS `.rtfd`-Pakete

---

## Lizenz

Veröffentlicht unter der [MIT-Lizenz](LICENSE).
Autor: Jonathan Klatchko
