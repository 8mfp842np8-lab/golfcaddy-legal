# Changelog

Alle nennenswerten Aenderungen an diesem Repository.

## [v1.0.0] - 2026-08-30

### Neu
- **Kickbase-MCP-Anbindung**: Claude kann ueber einen MCP-Server direkt auf
  Kickbase zugreifen — Kader, Budget, Transfermarkt, Liga-Wertung,
  Marktwertverlauf, Spielerstatistiken und Live-Daten (41 Tools).
  - Eingebunden wird [torstendunkel/kickbase-api-mcp](https://github.com/torstendunkel/kickbase-api-mcp)
    (MIT), gebaut auf dem offiziellen MCP-SDK.
  - `scripts/setup-kickbase-mcp.sh` klont den Server nach `vendor/`,
    installiert die Abhaengigkeiten und baut ihn; erneutes Ausfuehren
    aktualisiert ihn.
  - `.mcp.json` registriert den Server automatisch in diesem Projekt; der
    Pfad laesst sich ueber `KICKBASE_MCP_SERVER` umbiegen.
  - Einrichtung, Konfiguration und Hinweise zu den schreibenden Tools stehen
    in `docs/kickbase-mcp.md`.

### Bestand
- `datenschutz.html` (Datenschutzerklaerung SmartCaddie) bleibt unveraendert.
