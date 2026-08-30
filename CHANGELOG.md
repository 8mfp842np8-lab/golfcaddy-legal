# Changelog

Alle nennenswerten Aenderungen an diesem Repository.

## [v1.0.0] - 2026-08-30

### Neu
- **Kickbase MCP-Server** (`kickbase-mcp/`): MCP-Server ohne externe
  Abhaengigkeiten fuer die inoffizielle Kickbase-API v4.
  - 18 lesende Tools: Ligen, Kader, Budget, Transfermarkt, Liga-Wertung,
    Aufstellung, Spielerdetails, Marktwertverlauf, Punkteverlauf,
    Spielersuche, Bundesliga-Tabelle, Spielplan, Aktivitaeten-Feed,
    Feld-Glossar und ein generischer `/v4/`-GET-Endpunkt.
  - 5 schreibende Tools (Markt listen/entfernen, Gebot abgeben, Angebot
    beantworten, Aufstellung speichern), standardmaessig deaktiviert und
    erst mit `KICKBASE_ENABLE_WRITES=1` sichtbar.
  - Login per E-Mail/Passwort oder fertigem Token, automatische
    Token-Erneuerung bei HTTP 401, Selbst-Drosselung der Anfragen.
  - Antworten enthalten die Rohdaten plus eine Legende der abgekuerzten
    Feldnamen.
- `.mcp.json`: Der Server wird von Claude Code in diesem Projekt automatisch
  geladen.
- GitHub-Actions-Workflow: Unit-Tests auf Python 3.10 und 3.12 sowie ein
  Smoke-Test des MCP-Handshakes.

### Bestand
- `datenschutz.html` (Datenschutzerklaerung SmartCaddie) bleibt unveraendert.
