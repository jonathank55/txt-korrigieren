#!/usr/bin/env bash
# ==============================================================================
# txt-korrigieren — Deterministische Text-, Orthografie- und Stilkorrektur-Engine
# Installationsskript für macOS und Linux
# ==============================================================================

set -e

echo "=== Installation von txt-korrigieren ==="

# 1. Zielverzeichnis im PATH ermitteln
INSTALL_DIR=""
if [ -d "$HOME/.local/bin" ] && [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
    INSTALL_DIR="$HOME/.local/bin"
elif [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
else
    mkdir -p "$HOME/.local/bin"
    INSTALL_DIR="$HOME/.local/bin"
    echo "Hinweis: Bitte stellen Sie sicher, dass $HOME/.local/bin in Ihrem PATH liegt."
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. Abhängigkeiten installieren
echo "Prüfe Python-Abhängigkeiten..."
if command -v pip3 >/dev/null 2>&1; then
    pip3 install duden --break-system-packages >/dev/null 2>&1 || pip3 install duden >/dev/null 2>&1 || true
fi

# 3. Binaries und Module installieren
echo "Installiere txt-korrigieren nach $INSTALL_DIR..."
cp "$SCRIPT_DIR/txt-korrigieren" "$INSTALL_DIR/txt-korrigieren"
chmod +x "$INSTALL_DIR/txt-korrigieren"

if [ -f "$SCRIPT_DIR/duden_orthography_engine.py" ]; then
    cp "$SCRIPT_DIR/duden_orthography_engine.py" "$INSTALL_DIR/duden_orthography_engine.py"
fi

# 4. macOS native SpellBridge kompilieren & installieren
if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "Kompiliere native macOS SpellBridge..."
    if command -v clang >/dev/null 2>&1 && [ -f "$SCRIPT_DIR/spell_bridge.m" ]; then
        clang -dynamiclib -O3 -framework Cocoa "$SCRIPT_DIR/spell_bridge.m" -o "$INSTALL_DIR/libspell.dylib" 2>/dev/null || true
    fi
fi

echo "=============================================================================="
echo "ERFOLG: txt-korrigieren wurde erfolgreich installiert!"
echo "Befehl: txt-korrigieren [DATEI] [OPTIONEN]"
echo "Hilfe:  txt-korrigieren -h"
echo "Stil:   txt-korrigieren -s [DATEI]"
echo "=============================================================================="
