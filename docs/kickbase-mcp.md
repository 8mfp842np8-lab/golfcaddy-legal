# Kickbase-MCP-Server

Dieses Projekt bindet den MCP-Server
[torstendunkel/kickbase-api-mcp](https://github.com/torstendunkel/kickbase-api-mcp)
ein (MIT-Lizenz). Damit greift Claude direkt auf Kickbase zu: Kader, Budget,
Transfermarkt, Liga-Wertung, Marktwertverlauf, Spielerstatistiken und
Live-Daten — 41 Tools.

Der Server wird **nicht** mit eingecheckt. Er wird nach `vendor/` geklont und
dort gebaut, damit Updates einfach per `git pull` kommen.

## Einrichten

```bash
./scripts/setup-kickbase-mcp.sh
```

Das Skript klont den Server nach `vendor/kickbase-api-mcp/`, installiert die
Abhaengigkeiten und baut ihn. Voraussetzung ist Node.js ab Version 18.
Nochmal ausfuehren aktualisiert den Server auf den neuesten Stand.

Danach die Zugangsdaten setzen — dieselben wie in der Kickbase-App:

```bash
export KICKBASE_EMAIL="deine@mail.de"
export KICKBASE_PASSWORD="dein-passwort"
```

Die `.mcp.json` im Projektwurzelverzeichnis registriert den Server
automatisch, sobald Claude Code neu startet. Liegt der Server woanders,
zeigt `KICKBASE_MCP_SERVER` auf die `dist/index.js`:

```bash
export KICKBASE_MCP_SERVER="/anderer/pfad/mcp-server/dist/index.js"
```

## Ausprobieren

```
> Welche Kickbase-Ligen habe ich?
> Zeig mir meinen Kader und wer im Marktwert faellt.
> Was steht gerade unter 5 Mio auf dem Transfermarkt?
```

## Konfiguration

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `KICKBASE_EMAIL` / `KICKBASE_PASSWORD` | — | Zugangsdaten fuer den automatischen Login |
| `KICKBASE_TOKEN` | — | Fertiger Bearer-Token statt Login |
| `KICKBASE_MCP_SERVER` | `vendor/kickbase-api-mcp/mcp-server/dist/index.js` | Pfad zum gebauten Server |
| `KICKBASE_CACHE_TTL` | `3600` | Cache-Dauer in Sekunden, `0` schaltet den Cache ab |
| `KICKBASE_KEEP_IMAGES` | nicht gesetzt | `1` behaelt Bildpfade in den Antworten |

## Schreibende Tools

Von den 41 Tools veraendern 11 deinen Account. Zwei davon hat der Autor des
Servers bewusst hart abgeschaltet — sie sind zwar sichtbar, brechen aber mit
einer Fehlermeldung ab:

- `kickbase_sell_player`
- `kickbase_accept_offer`

Sein Kommentar im Code dazu: *"LLMs have been known to sell players
unprompted/incorrectly."*

Aktiv bleiben unter anderem `kickbase_place_offer` (gibt Spielgeld aus),
`kickbase_fill_lineup`, `kickbase_decline_offer` und
`kickbase_withdraw_offer`. Claude Code fragt vor jedem Tool-Aufruf nach —
bestaetige diese Tools also nur bewusst und nutze keinen Modus, der
Berechtigungen pauschal durchwinkt.

## Hinweis zur API

Kickbase bietet keine offizielle oeffentliche API. Der Server spricht mit den
internen v4-Endpunkten der App, dokumentiert von der Community
([kevinskyba/kickbase-api-doc](https://github.com/kevinskyba/kickbase-api-doc)).
Endpunkte koennen sich jederzeit aendern, und zu viele Anfragen koennen zur
Sperrung des Accounts fuehren. Weder der Server noch dieses Projekt stehen in
Verbindung zur Kickbase GmbH.
