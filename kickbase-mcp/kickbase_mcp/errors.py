"""Fehlertypen des Kickbase-MCP-Servers."""


class KickbaseError(Exception):
    """Basisklasse fuer alle Fehler dieses Servers."""


class KickbaseAuthError(KickbaseError):
    """Login fehlgeschlagen oder Token abgelaufen/ungueltig."""


class KickbaseHTTPError(KickbaseError):
    """Die Kickbase-API hat einen Fehlerstatus geliefert."""

    def __init__(self, status: int, path: str, body: str) -> None:
        self.status = status
        self.path = path
        self.body = body
        super().__init__(f"HTTP {status} fuer {path}: {body[:400]}")


class KickbaseConfigError(KickbaseError):
    """Zugangsdaten oder Konfiguration fehlen bzw. sind unvollstaendig."""
