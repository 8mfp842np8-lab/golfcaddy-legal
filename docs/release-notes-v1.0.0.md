# v1.0.0 - Kickbase-MCP-Anbindung

Claude kann jetzt direkt auf Kickbase zugreifen: Kader, Budget, Transfermarkt, Liga-Wertung, Marktwertverlauf, Spielerstatistiken und Live-Daten.

### Was drin ist

- Eingebunden wird der MCP-Server [torstendunkel/kickbase-api-mcp](https://github.com/torstendunkel/kickbase-api-mcp) (MIT-Lizenz) mit **41 Tools**, gebaut auf dem offiziellen MCP-SDK.
- `scripts/setup-kickbase-mcp.sh` klont den Server nach `vendor/`, installiert die Abhaengigkeiten und baut ihn. Erneutes Ausfuehren aktualisiert ihn.
- `.mcp.json` registriert den Server automatisch in diesem Projekt; ueber `KICKBASE_MCP_SERVER` laesst sich ein anderer Pfad setzen.
- Doku unter [`docs/kickbase-mcp.md`](https://github.com/8mfp842np8-lab/golfcaddy-legal/blob/main/docs/kickbase-mcp.md).

### Einrichtung

```bash
./scripts/setup-kickbase-mcp.sh
export KICKBASE_EMAIL="deine@mail.de"
export KICKBASE_PASSWORD="dein-passwort"
```

### Hinweise

11 der 41 Tools veraendern den Account. `kickbase_sell_player` und `kickbase_accept_offer` sind vom Autor des Servers bewusst hart abgeschaltet; `kickbase_place_offer` und `kickbase_fill_lineup` sind aktiv. Claude Code fragt vor jedem Tool-Aufruf nach.

Kickbase bietet keine offizielle oeffentliche API. Der Server spricht mit den internen v4-Endpunkten; Endpunkte koennen sich jederzeit aendern, zu viele Anfragen koennen zur Account-Sperre fuehren. Keine Verbindung zur Kickbase GmbH.
