# Kickbase MCP-Server

Ein MCP-Server (Model Context Protocol), der Claude Zugriff auf deinen
Kickbase-Account gibt: Kader, Budget, Transfermarkt, Liga-Tabelle,
Marktwertverlauf, Spielerstatistiken — und auf Wunsch auch Gebote und
Aufstellung.

* **Keine Abhaengigkeiten.** Nur Python 3.10+ aus der Standardbibliothek,
  kein `pip install`, kein Build-Schritt.
* **Lesend per Standard.** Alles, was deinen Account veraendert (Gebote,
  Verkaeufe, Aufstellung), ist deaktiviert, bis du es ausdruecklich
  freischaltest.

## Wichtiger Hinweis

Kickbase bietet **keine offizielle oeffentliche API**. Dieser Server spricht
mit den internen v4-Endpunkten der App, dokumentiert von der Community
([kevinskyba/kickbase-api-doc](https://github.com/kevinskyba/kickbase-api-doc)).
Daraus folgt:

* Endpunkte koennen sich jederzeit ohne Vorankuendigung aendern.
* Zu viele Anfragen koennen zur Sperrung deines Accounts fuehren. Der Server
  drosselt sich deshalb selbst (Standard: max. 4 Anfragen pro Sekunde,
  einstellbar ueber `KICKBASE_MIN_REQUEST_INTERVAL`).
* Das Projekt steht in keiner Verbindung zur Kickbase GmbH.

## Einrichtung

### 1. Zugangsdaten hinterlegen

Der Server meldet sich mit deinen normalen Kickbase-Zugangsdaten an und haelt
den Token nur im Arbeitsspeicher. Lege die Werte als Umgebungsvariablen an,
damit sie nicht im Repository landen:

```bash
export KICKBASE_EMAIL="deine@mail.de"
export KICKBASE_PASSWORD="dein-passwort"
```

Alternativ kannst du einen bereits vorhandenen Token setzen
(`KICKBASE_TOKEN`); dann werden E-Mail und Passwort nicht benoetigt, der
Token laeuft aber nach etwa einer Woche ab.

### 2. Server in Claude Code registrieren

Im Repository liegt bereits eine `.mcp.json`, die Claude Code beim Start
dieses Projekts automatisch einliest. Manuell geht es so:

```bash
claude mcp add kickbase \
  --env KICKBASE_EMAIL="$KICKBASE_EMAIL" \
  --env KICKBASE_PASSWORD="$KICKBASE_PASSWORD" \
  -- python3 /pfad/zu/golfcaddy-legal/kickbase-mcp/run_server.py
```

`run_server.py` legt seinen eigenen Ordner selbst auf den Importpfad und
laeuft deshalb aus jedem Arbeitsverzeichnis.

Fuer Claude Desktop traegst du denselben Befehl in
`claude_desktop_config.json` ein:

```json
{
  "mcpServers": {
    "kickbase": {
      "command": "python3",
      "args": ["/pfad/zu/golfcaddy-legal/kickbase-mcp/run_server.py"],
      "env": {
        "KICKBASE_EMAIL": "deine@mail.de",
        "KICKBASE_PASSWORD": "dein-passwort"
      }
    }
  }
}
```

### 3. Ausprobieren

```
> Welche Kickbase-Ligen habe ich?
> Zeig mir meinen Kader und welche Spieler im Marktwert fallen.
> Was steht gerade auf dem Transfermarkt unter 5 Mio?
```

## Tools

### Lesend (immer verfuegbar)

| Tool | Zweck |
| --- | --- |
| `kickbase_me` | Eigenes Benutzerprofil |
| `kickbase_leagues` | Alle eigenen Ligen inkl. `league_id` |
| `kickbase_league_overview` | Liga-Einstellungen, Spieltag, Mitmanager |
| `kickbase_budget` | Budget, Kontostand und Teamwert |
| `kickbase_squad` | Eigener Kader |
| `kickbase_manager_squad` | Kader eines Mitmanagers |
| `kickbase_market` | Transfermarkt mit Preisen und Angeboten |
| `kickbase_ranking` | Liga-Wertung, gesamt oder pro Spieltag |
| `kickbase_lineup` | Aktuelle Aufstellung |
| `kickbase_player` | Spielerdetails im Liga-Kontext |
| `kickbase_player_market_value` | Marktwertverlauf |
| `kickbase_player_performance` | Punkte pro Spieltag |
| `kickbase_search_players` | Spielersuche im Wettbewerb |
| `kickbase_competition_table` | Bundesliga-Tabelle |
| `kickbase_matchdays` | Spielplan und Ergebnisse |
| `kickbase_activity_feed` | Transfers und Marktwertaenderungen der Liga |
| `kickbase_glossary` | Erklaerung der Feldabkuerzungen |
| `kickbase_raw_get` | Beliebiger lesender `/v4/`-Endpunkt |

### Schreibend (nur mit `KICKBASE_ENABLE_WRITES=1`)

| Tool | Zweck |
| --- | --- |
| `kickbase_list_player_on_market` | Spieler auf den Markt stellen |
| `kickbase_remove_player_from_market` | Spieler vom Markt nehmen |
| `kickbase_make_offer` | Gebot abgeben |
| `kickbase_respond_to_offer` | Angebot annehmen oder ablehnen |
| `kickbase_set_lineup` | Aufstellung speichern |

Ohne das Flag tauchen diese Tools nicht einmal in der Tool-Liste auf. Sie
geben echtes Spielgeld aus und aendern deine Aufstellung — schalte sie nur
frei, wenn du das willst.

## Konfiguration

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `KICKBASE_EMAIL` | — | E-Mail des Kickbase-Kontos |
| `KICKBASE_PASSWORD` | — | Passwort des Kickbase-Kontos |
| `KICKBASE_TOKEN` | — | Fertiger Bearer-Token statt Login |
| `KICKBASE_ENABLE_WRITES` | `0` | `1` schaltet schreibende Tools frei |
| `KICKBASE_MIN_REQUEST_INTERVAL` | `0.25` | Mindestabstand zwischen Anfragen (Sekunden) |
| `KICKBASE_TIMEOUT` | `20` | HTTP-Timeout in Sekunden |
| `KICKBASE_MAX_RESPONSE_CHARS` | `60000` | Kuerzt sehr grosse Antworten |
| `KICKBASE_BASE_URL` | `https://api.kickbase.com` | Nur fuer Tests |

## Antwortformat

Die Kickbase-API benutzt stark abgekuerzte Feldnamen (`mv`, `pos`, `st`).
Der Server liefert die Rohdaten unveraendert unter `daten` und haengt unter
`_legende` nur die Erklaerungen der tatsaechlich vorkommenden Felder an:

```json
{
  "daten": { "it": [{ "pn": "Musiala", "mv": 30000000, "pos": 3 }] },
  "_legende": {
    "mv": "Marktwert in EUR",
    "pn": "Spielername",
    "pos": "Position (1=TW, 2=ABW, 3=MIT, 4=STU)"
  }
}
```

Die Legende stammt aus der Community-Dokumentation und ist nicht garantiert
vollstaendig.

## Tests

```bash
cd kickbase-mcp
python3 -m unittest discover -s tests -t . -v
```

Die Tests laufen komplett ohne Netzwerk: der HTTP-Transport wird durch ein
Test-Double ersetzt.

## Aufbau

```
run_server.py   Startskript fuer die MCP-Konfiguration
kickbase_mcp/
  client.py     HTTP, Login, Token-Erneuerung, Rate-Limiting
  tools.py      Tool-Definitionen und Endpunkt-Zuordnung
  server.py     JSON-RPC-2.0-Schleife ueber stdio
  glossary.py   Uebersetzung der Feldabkuerzungen
  errors.py     Fehlertypen
```
