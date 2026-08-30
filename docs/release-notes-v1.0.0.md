# v1.0.0 - Kickbase MCP-Server


Erste Version des MCP-Servers, mit dem Claude direkt auf Kickbase zugreifen kann: Kader, Budget, Transfermarkt, Liga-Wertung, Marktwertverlauf und Spielerstatistiken.

### Highlights

- **Ohne Installation lauffaehig** - nur Python 3.10+ aus der Standardbibliothek, kein `pip install`, kein Build-Schritt.
- **18 lesende Tools**: Ligen, Kader, Budget, Transfermarkt, Liga-Wertung, Aufstellung, Spielerdetails, Marktwert- und Punkteverlauf, Spielersuche, Bundesliga-Tabelle, Spielplan, Aktivitaeten-Feed, Feld-Glossar sowie ein generischer `/v4/`-GET-Endpunkt.
- **5 schreibende Tools** (Spieler listen/entfernen, Gebot abgeben, Angebot beantworten, Aufstellung speichern) sind standardmaessig deaktiviert und erscheinen erst mit `KICKBASE_ENABLE_WRITES=1` in der Tool-Liste.
- **Robuste Anmeldung**: Login per E-Mail/Passwort oder fertigem Token, automatische Token-Erneuerung bei HTTP 401, Selbst-Drosselung der Anfragen an die inoffizielle API.
- **Lesbare Antworten**: Rohdaten bleiben unveraendert, dazu kommt eine Legende der abgekuerzten Feldnamen (`mv`, `pos`, `st` ...).
- **48 Unit-Tests** ohne Netzwerkzugriff plus CI-Workflow mit Handshake-Smoke-Test auf Python 3.10 und 3.12.

### Einrichtung

```bash
export KICKBASE_EMAIL="deine@mail.de"
export KICKBASE_PASSWORD="dein-passwort"
```

Die mitgelieferte `.mcp.json` registriert den Server in diesem Projekt automatisch. Details in [`kickbase-mcp/README.md`](https://github.com/8mfp842np8-lab/golfcaddy-legal/blob/claude/kickbase-mcp-integration-gphul1/kickbase-mcp/README.md).

### Hinweis

Kickbase bietet keine offizielle oeffentliche API. Der Server spricht mit den internen v4-Endpunkten, dokumentiert von der Community. Endpunkte koennen sich jederzeit aendern; zu viele Anfragen koennen zur Account-Sperre fuehren. Das Projekt steht in keiner Verbindung zur Kickbase GmbH.
