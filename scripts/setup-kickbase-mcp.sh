#!/usr/bin/env bash
# Holt und baut den Kickbase-MCP-Server von torstendunkel/kickbase-api-mcp.
# Der Server selbst wird nicht mit eingecheckt (siehe .gitignore), sondern
# hier nach vendor/ geklont und gebaut.
set -euo pipefail

UPSTREAM="https://github.com/torstendunkel/kickbase-api-mcp"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$ROOT/vendor/kickbase-api-mcp"
SERVER="$TARGET/mcp-server"

command -v node >/dev/null || { echo "Fehler: node wird benoetigt (>= 18)." >&2; exit 1; }
command -v npm  >/dev/null || { echo "Fehler: npm wird benoetigt." >&2; exit 1; }

if [ -d "$TARGET/.git" ]; then
  echo "==> Aktualisiere $TARGET"
  git -C "$TARGET" pull --ff-only
else
  echo "==> Klone $UPSTREAM nach $TARGET"
  git clone --depth 1 "$UPSTREAM" "$TARGET"
fi

echo "==> Installiere Abhaengigkeiten"
npm --prefix "$SERVER" install --no-audit --no-fund

echo "==> Baue den Server"
npm --prefix "$SERVER" run build

echo
echo "Fertig. Server liegt unter:"
echo "  $SERVER/dist/index.js"
echo
echo "Zugangsdaten setzen und Claude Code neu starten:"
echo "  export KICKBASE_EMAIL='deine@mail.de'"
echo "  export KICKBASE_PASSWORD='dein-passwort'"
