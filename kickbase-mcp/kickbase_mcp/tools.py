"""Definition der MCP-Tools rund um die Kickbase-API."""

from __future__ import annotations

import urllib.parse
from typing import Any, Callable, Mapping

from .client import KickbaseClient
from .errors import KickbaseError
from .glossary import FIELDS, POSITIONS, STATUS

Handler = Callable[[KickbaseClient, Mapping[str, Any]], Any]

DEFAULT_COMPETITION = "1"  # 1 = Bundesliga


class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        schema: dict[str, Any],
        handler: Handler,
        writes: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.schema = schema
        self.handler = handler
        self.writes = writes

    def spec(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.schema,
        }


REGISTRY: dict[str, Tool] = {}


def tool(
    name: str,
    description: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
    writes: bool = False,
) -> Callable[[Handler], Handler]:
    def decorate(handler: Handler) -> Handler:
        schema = {
            "type": "object",
            "properties": properties or {},
            "required": required or [],
            "additionalProperties": False,
        }
        REGISTRY[name] = Tool(name, description, schema, handler, writes)
        return handler

    return decorate


def _quote(value: Any) -> str:
    return urllib.parse.quote(str(value), safe="")


def _league(args: Mapping[str, Any]) -> str:
    league_id = args.get("league_id")
    if not league_id:
        raise KickbaseError(
            "league_id fehlt. Mit 'kickbase_leagues' die verfuegbaren Ligen auflisten."
        )
    return _quote(league_id)


# --------------------------------------------------------------- Lesetools

_LEAGUE_ARG = {"league_id": {"type": "string", "description": "ID der Kickbase-Liga."}}
_PLAYER_ARG = {"player_id": {"type": "string", "description": "ID des Spielers."}}


@tool(
    "kickbase_me",
    "Gibt das eigene Kickbase-Benutzerprofil zurueck (Name, ID, Einstellungen).",
)
def _me(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get("/v4/user/me")


@tool(
    "kickbase_leagues",
    "Listet alle Ligen auf, in denen der angemeldete Manager spielt. "
    "Liefert die league_id, die fast alle anderen Tools benoetigen.",
)
def _leagues(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get("/v4/leagues/selection")


@tool(
    "kickbase_league_overview",
    "Uebersicht einer Liga: Einstellungen, Spieltag, optional die Mitmanager.",
    {
        **_LEAGUE_ARG,
        "include_managers": {
            "type": "boolean",
            "description": "Mitmanager und Duelle mitliefern (Standard: true).",
        },
    },
    ["league_id"],
)
def _league_overview(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    include = args.get("include_managers", True)
    return client.get(
        f"/v4/leagues/{_league(args)}/overview",
        includeManagersAndBattles=str(bool(include)).lower(),
    )


@tool(
    "kickbase_budget",
    "Zeigt Budget, Teamwert und Kontostand des eigenen Managers in einer Liga.",
    _LEAGUE_ARG,
    ["league_id"],
)
def _budget(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    league = _league(args)
    return {
        "budget": client.get(f"/v4/leagues/{league}/me/budget"),
        "me": client.get(f"/v4/leagues/{league}/me"),
    }


@tool(
    "kickbase_squad",
    "Listet den eigenen Kader in einer Liga inklusive Marktwerten und Punkten.",
    _LEAGUE_ARG,
    ["league_id"],
)
def _squad(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get(f"/v4/leagues/{_league(args)}/squad")


@tool(
    "kickbase_manager_squad",
    "Zeigt den Kader eines anderen Managers in der Liga.",
    {
        **_LEAGUE_ARG,
        "manager_id": {"type": "string", "description": "ID des Managers."},
    },
    ["league_id", "manager_id"],
)
def _manager_squad(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get(
        f"/v4/leagues/{_league(args)}/managers/{_quote(args['manager_id'])}/squad"
    )


@tool(
    "kickbase_market",
    "Aktueller Transfermarkt der Liga: gelistete Spieler, Preise, Restlaufzeiten "
    "und vorliegende Angebote.",
    _LEAGUE_ARG,
    ["league_id"],
)
def _market(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get(f"/v4/leagues/{_league(args)}/market")


@tool(
    "kickbase_ranking",
    "Tabelle der Liga (Gesamtwertung oder ein einzelner Spieltag).",
    {
        **_LEAGUE_ARG,
        "matchday": {
            "type": "integer",
            "description": "Spieltag; ohne Angabe die Gesamtwertung.",
        },
    },
    ["league_id"],
)
def _ranking(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get(
        f"/v4/leagues/{_league(args)}/ranking", dayNumber=args.get("matchday")
    )


@tool(
    "kickbase_lineup",
    "Zeigt die aktuell aufgestellte Startelf inklusive Formation.",
    _LEAGUE_ARG,
    ["league_id"],
)
def _lineup(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get(f"/v4/leagues/{_league(args)}/lineup")


@tool(
    "kickbase_player",
    "Detaildaten zu einem Spieler im Kontext der Liga (Marktwert, Status, Besitzer).",
    {**_LEAGUE_ARG, **_PLAYER_ARG},
    ["league_id", "player_id"],
)
def _player(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get(
        f"/v4/leagues/{_league(args)}/players/{_quote(args['player_id'])}"
    )


@tool(
    "kickbase_player_market_value",
    "Marktwertverlauf eines Spielers. timeframe ist der Zeitraum-Code der API "
    "(gebraeuchlich: 1, 3, 6, 12, 24).",
    {
        **_LEAGUE_ARG,
        **_PLAYER_ARG,
        "timeframe": {"type": "string", "description": "Zeitraum-Code, Standard '3'."},
    },
    ["league_id", "player_id"],
)
def _player_market_value(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    timeframe = _quote(args.get("timeframe") or "3")
    return client.get(
        f"/v4/leagues/{_league(args)}/players/"
        f"{_quote(args['player_id'])}/marketvalue/{timeframe}"
    )


@tool(
    "kickbase_player_performance",
    "Punkte- und Einsatzverlauf eines Spielers ueber die Spieltage.",
    {**_LEAGUE_ARG, **_PLAYER_ARG},
    ["league_id", "player_id"],
)
def _player_performance(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get(
        f"/v4/leagues/{_league(args)}/players/"
        f"{_quote(args['player_id'])}/performance"
    )


@tool(
    "kickbase_search_players",
    "Sucht Spieler im Wettbewerb nach Namen, optional im Kontext einer Liga.",
    {
        "query": {"type": "string", "description": "Suchbegriff, z. B. 'Musiala'."},
        "league_id": {"type": "string", "description": "Optionaler Liga-Kontext."},
        "competition_id": {
            "type": "string",
            "description": "Wettbewerb, Standard '1' (Bundesliga).",
        },
        "limit": {"type": "integer", "description": "Maximale Trefferzahl."},
    },
    ["query"],
)
def _search_players(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    competition = _quote(args.get("competition_id") or DEFAULT_COMPETITION)
    return client.get(
        f"/v4/competitions/{competition}/players/search",
        query=args["query"],
        leagueId=args.get("league_id"),
        max=args.get("limit"),
    )


@tool(
    "kickbase_competition_table",
    "Bundesliga-Tabelle des Wettbewerbs (nicht die Liga-Wertung).",
    {
        "competition_id": {
            "type": "string",
            "description": "Wettbewerb, Standard '1' (Bundesliga).",
        }
    },
)
def _competition_table(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    competition = _quote(args.get("competition_id") or DEFAULT_COMPETITION)
    return client.get(f"/v4/competitions/{competition}/table")


@tool(
    "kickbase_matchdays",
    "Spielplan und Ergebnisse der Spieltage eines Wettbewerbs.",
    {
        "competition_id": {
            "type": "string",
            "description": "Wettbewerb, Standard '1' (Bundesliga).",
        }
    },
)
def _matchdays(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    competition = _quote(args.get("competition_id") or DEFAULT_COMPETITION)
    return client.get(f"/v4/competitions/{competition}/matchdays")


@tool(
    "kickbase_activity_feed",
    "Aktivitaeten der Liga: Transfers, Angebote, Marktwertaenderungen.",
    {
        **_LEAGUE_ARG,
        "start": {"type": "integer", "description": "Offset fuer das Blaettern."},
        "limit": {"type": "integer", "description": "Anzahl der Eintraege."},
        "filter": {"type": "string", "description": "Optionaler Filtercode der API."},
    },
    ["league_id"],
)
def _activity_feed(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.get(
        f"/v4/leagues/{_league(args)}/activitiesFeed",
        start=args.get("start"),
        max=args.get("limit"),
        filter=args.get("filter"),
    )


@tool(
    "kickbase_glossary",
    "Erklaert die abgekuerzten Feldnamen, Positions- und Statuscodes der API.",
)
def _glossary(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return {
        "hinweis": (
            "Community-Dokumentation der inoffiziellen API - kann unvollstaendig sein."
        ),
        "felder": FIELDS,
        "positionen": {str(k): v for k, v in POSITIONS.items()},
        "status": {str(k): v for k, v in STATUS.items()},
    }


@tool(
    "kickbase_raw_get",
    "Fuehrt einen beliebigen lesenden GET-Aufruf gegen die Kickbase-API v4 aus. "
    "Nur fuer Endpunkte, fuer die es kein eigenes Tool gibt.",
    {
        "path": {
            "type": "string",
            "description": "Pfad beginnend mit /v4/, z. B. '/v4/base/overview'.",
        },
        "query": {
            "type": "object",
            "description": "Optionale Query-Parameter.",
            "additionalProperties": True,
        },
    },
    ["path"],
)
def _raw_get(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    path = str(args["path"])
    if not path.startswith("/v4/"):
        raise KickbaseError("path muss mit '/v4/' beginnen.")
    if ".." in path:
        raise KickbaseError("path darf kein '..' enthalten.")
    query = args.get("query") or {}
    if not isinstance(query, dict):
        raise KickbaseError("query muss ein Objekt sein.")
    return client.request("GET", path, query=query)


# -------------------------------------------------------------- Schreibtools


@tool(
    "kickbase_list_player_on_market",
    "Stellt einen eigenen Spieler zum angegebenen Preis auf den Transfermarkt. "
    "Nur aktiv, wenn KICKBASE_ENABLE_WRITES=1 gesetzt ist.",
    {
        **_LEAGUE_ARG,
        **_PLAYER_ARG,
        "price": {"type": "number", "description": "Angebotspreis in Euro."},
    },
    ["league_id", "player_id", "price"],
    writes=True,
)
def _list_on_market(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.post(
        f"/v4/leagues/{_league(args)}/market",
        body={"pi": str(args["player_id"]), "prc": args["price"]},
    )


@tool(
    "kickbase_remove_player_from_market",
    "Nimmt einen eigenen Spieler wieder vom Transfermarkt. "
    "Nur aktiv, wenn KICKBASE_ENABLE_WRITES=1 gesetzt ist.",
    {**_LEAGUE_ARG, **_PLAYER_ARG},
    ["league_id", "player_id"],
    writes=True,
)
def _remove_from_market(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.delete(
        f"/v4/leagues/{_league(args)}/market/{_quote(args['player_id'])}"
    )


@tool(
    "kickbase_make_offer",
    "Gibt ein Gebot auf einen Spieler auf dem Transfermarkt ab. Gibt echtes "
    "Spielgeld aus. Nur aktiv, wenn KICKBASE_ENABLE_WRITES=1 gesetzt ist.",
    {
        **_LEAGUE_ARG,
        **_PLAYER_ARG,
        "price": {"type": "number", "description": "Gebot in Euro."},
    },
    ["league_id", "player_id", "price"],
    writes=True,
)
def _make_offer(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    return client.post(
        f"/v4/leagues/{_league(args)}/market/{_quote(args['player_id'])}/offers",
        body={"price": args["price"]},
    )


@tool(
    "kickbase_respond_to_offer",
    "Nimmt ein Angebot fuer einen eigenen Spieler an oder lehnt es ab. "
    "Nur aktiv, wenn KICKBASE_ENABLE_WRITES=1 gesetzt ist.",
    {
        **_LEAGUE_ARG,
        **_PLAYER_ARG,
        "offer_id": {"type": "string", "description": "ID des Angebots."},
        "decision": {
            "type": "string",
            "enum": ["accept", "decline"],
            "description": "'accept' annehmen, 'decline' ablehnen.",
        },
    },
    ["league_id", "player_id", "offer_id", "decision"],
    writes=True,
)
def _respond_to_offer(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    decision = args["decision"]
    if decision not in ("accept", "decline"):
        raise KickbaseError("decision muss 'accept' oder 'decline' sein.")
    return client.post(
        f"/v4/leagues/{_league(args)}/market/{_quote(args['player_id'])}"
        f"/offers/{_quote(args['offer_id'])}/{decision}"
    )


@tool(
    "kickbase_set_lineup",
    "Speichert eine Aufstellung. players enthaelt die Spieler-IDs der Startelf. "
    "Nur aktiv, wenn KICKBASE_ENABLE_WRITES=1 gesetzt ist.",
    {
        **_LEAGUE_ARG,
        "formation": {"type": "string", "description": "Formation, z. B. '4-4-2'."},
        "players": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Spieler-IDs der Startelf in Aufstellungsreihenfolge.",
        },
    },
    ["league_id", "formation", "players"],
    writes=True,
)
def _set_lineup(client: KickbaseClient, args: Mapping[str, Any]) -> Any:
    players = args["players"]
    if not isinstance(players, list) or not players:
        raise KickbaseError("players muss eine nicht-leere Liste von Spieler-IDs sein.")
    return client.post(
        f"/v4/leagues/{_league(args)}/lineup",
        body={"type": args["formation"], "players": [str(p) for p in players]},
    )


def available_tools(allow_writes: bool) -> list[Tool]:
    return [t for t in REGISTRY.values() if allow_writes or not t.writes]
