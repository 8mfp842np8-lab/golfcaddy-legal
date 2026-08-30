"""Uebersetzung der abgekuerzten Kickbase-Feldnamen.

Die Kickbase-API liefert stark abgekuerzte Schluessel ("mv", "pos", "st").
Diese Zuordnung stammt aus der Community-Dokumentation der inoffiziellen
API und ist deshalb *nicht* garantiert vollstaendig oder fuer jeden
Endpunkt korrekt. Der Server liefert die Rohdaten immer unveraendert mit
und haengt die Erklaerungen nur als separate Legende an.
"""

from __future__ import annotations

from typing import Any

FIELDS: dict[str, str] = {
    "i": "ID",
    "id": "ID",
    "n": "Name",
    "fn": "Vorname",
    "ln": "Nachname",
    "unm": "Managername",
    "u": "Benutzer/Manager",
    "ui": "Benutzer-ID",
    "uid": "Benutzer-ID",
    "pi": "Spieler-ID",
    "pn": "Spielername",
    "tid": "Team-ID (Bundesliga-Verein)",
    "tn": "Teamname",
    "t1": "Heimteam-ID",
    "t2": "Auswaertsteam-ID",
    "cpi": "Wettbewerbs-Spieler-ID",
    "pos": "Position (1=TW, 2=ABW, 3=MIT, 4=STU)",
    "st": "Status (0=fit, 1=verletzt, 2=angeschlagen, 4=Aufbautraining, 8=gesperrt)",
    "mv": "Marktwert in EUR",
    "mvt": "Marktwert-Trend (0=stabil, 1=steigend, 2=fallend)",
    "tfhmvt": "Marktwertaenderung der letzten 24 Stunden",
    "prc": "Preis / Angebotspreis in EUR",
    "p": "Punkte",
    "ap": "Durchschnittspunkte",
    "tp": "Gesamtpunkte",
    "lp": "Live-Punkte",
    "sp": "Punkte am Spieltag",
    "mdst": "Spieltag-Status",
    "day": "Spieltag",
    "dy": "Spieltag",
    "exs": "Restlaufzeit des Marktangebots in Sekunden",
    "exst": "Ablaufzeitpunkt des Marktangebots",
    "dt": "Datum/Zeitstempel",
    "b": "Budget in EUR",
    "bs": "Budget-Status",
    "tv": "Teamwert in EUR",
    "it": "Liste der Eintraege (items)",
    "ofc": "Anzahl der Angebote",
    "ofs": "Angebote (offers)",
    "sl": "Verkaeufer (seller)",
    "isn": "Von Kickbase eingestellt (kein echter Manager)",
    "iposl": "Auf dem Transfermarkt gelistet",
    "lst": "Listentyp",
    "shn": "Rueckennummer",
    "cv": "Aktueller Wert",
    "mdsum": "Spieltags-Zusammenfassung",
    "pim": "Spielerbild",
    "plpt": "Punkte pro Spiel",
    "sdmvt": "Marktwertaenderung seit dem letzten Tag",
    "trp": "Gesamtpunkte in der Liga",
    "cpl": "Aktueller Platz in der Liga",
    "shp": "Punkte-Anteil",
    "mdpts": "Punkte des Spieltags",
}

POSITIONS: dict[int, str] = {
    1: "Torwart",
    2: "Abwehr",
    3: "Mittelfeld",
    4: "Sturm",
}

STATUS: dict[int, str] = {
    0: "fit",
    1: "verletzt",
    2: "angeschlagen",
    4: "Aufbautraining",
    8: "gesperrt",
    16: "abwesend",
}


def _walk_keys(value: Any, found: set[str], depth: int = 0) -> None:
    if depth > 12:
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                found.add(key)
            _walk_keys(item, found, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _walk_keys(item, found, depth + 1)


def legend_for(payload: Any) -> dict[str, str]:
    """Liefert die bekannten Erklaerungen zu allen Feldern einer Antwort."""
    found: set[str] = set()
    _walk_keys(payload, found)
    return {key: FIELDS[key] for key in sorted(found) if key in FIELDS}
