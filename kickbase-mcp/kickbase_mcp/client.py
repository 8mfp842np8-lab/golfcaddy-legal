"""Schlanker HTTP-Client fuer die (inoffizielle) Kickbase-API v4.

Der Client kuemmert sich um Login, Token-Erneuerung, Rate-Limiting und das
Parsen der JSON-Antworten. Er benutzt ausschliesslich die Python-Standard-
bibliothek, damit der MCP-Server ohne Installationsschritt startet.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .errors import KickbaseAuthError, KickbaseConfigError, KickbaseHTTPError

DEFAULT_BASE_URL = "https://api.kickbase.com"
DEFAULT_USER_AGENT = "kickbase-mcp/1.0 (+https://github.com/8mfp842np8-lab/golfcaddy-legal)"
DEFAULT_TIMEOUT = 20.0
DEFAULT_MIN_INTERVAL = 0.25

# (status, headers, body)
Response = tuple[int, dict[str, str], bytes]
Transport = Callable[[str, str, dict[str, str], bytes | None, float], Response]


def _urllib_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    timeout: float,
) -> Response:
    request = urllib.request.Request(url, data=body, method=method)
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return (
                response.status,
                {k.lower(): v for k, v in response.headers.items()},
                response.read(),
            )
    except urllib.error.HTTPError as exc:  # Fehlerstatus liefert trotzdem einen Body
        return (
            exc.code,
            {k.lower(): v for k, v in (exc.headers or {}).items()},
            exc.read(),
        )
    except urllib.error.URLError as exc:
        raise KickbaseHTTPError(0, url, f"Netzwerkfehler: {exc.reason}") from exc


def _jwt_expiry(token: str) -> float | None:
    """Liest den ``exp``-Claim aus einem JWT, ohne die Signatur zu pruefen."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, binascii.Error):
        return None
    exp = claims.get("exp")
    return float(exp) if isinstance(exp, (int, float)) else None


def _parse_expiry(value: Any) -> float | None:
    """Wandelt ``tknex`` (ISO-8601) in einen Unix-Zeitstempel um."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _cookie_token(set_cookie: str) -> str | None:
    """Extrahiert das ``kkstrauth``-Cookie aus einem Set-Cookie-Header."""
    for chunk in set_cookie.split(","):
        for part in chunk.split(";"):
            name, _, value = part.strip().partition("=")
            if name.strip().lower() == "kkstrauth" and value:
                return value.strip()
    return None


class KickbaseClient:
    """Authentifizierter Zugriff auf ``https://api.kickbase.com``."""

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        token: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        transport: Transport | None = None,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.email = email
        self.password = password
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.min_interval = min_interval
        self._transport = transport or _urllib_transport
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._token = token
        self._token_expiry = _jwt_expiry(token) if token else None
        self._last_request_at = 0.0

    # ------------------------------------------------------------------ Auth

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None, **kwargs: Any
    ) -> "KickbaseClient":
        env = os.environ if env is None else env
        min_interval = env.get("KICKBASE_MIN_REQUEST_INTERVAL")
        return cls(
            email=env.get("KICKBASE_EMAIL") or None,
            password=env.get("KICKBASE_PASSWORD") or None,
            token=env.get("KICKBASE_TOKEN") or None,
            base_url=env.get("KICKBASE_BASE_URL") or DEFAULT_BASE_URL,
            timeout=float(env.get("KICKBASE_TIMEOUT") or DEFAULT_TIMEOUT),
            min_interval=(
                float(min_interval) if min_interval else DEFAULT_MIN_INTERVAL
            ),
            **kwargs,
        )

    @property
    def has_credentials(self) -> bool:
        return bool(self._token or (self.email and self.password))

    def _token_valid(self) -> bool:
        if not self._token:
            return False
        if self._token_expiry is None:
            return True
        # 60 Sekunden Puffer, damit kein Request in den Ablauf laeuft.
        return self._clock() < self._token_expiry - 60

    def login(self) -> dict[str, Any]:
        """Meldet sich mit E-Mail und Passwort an und speichert den Token."""
        if not (self.email and self.password):
            raise KickbaseConfigError(
                "Kein gueltiger Token und keine Zugangsdaten vorhanden. "
                "Setze KICKBASE_EMAIL und KICKBASE_PASSWORD (oder KICKBASE_TOKEN)."
            )
        status, headers, raw = self._send(
            "POST",
            "/v4/user/login",
            body={"em": self.email, "pass": self.password, "loy": False, "rep": {}},
            authenticated=False,
        )
        payload = self._decode(raw, "/v4/user/login")
        if status >= 400:
            raise KickbaseAuthError(
                f"Login fehlgeschlagen (HTTP {status}). "
                "Bitte E-Mail und Passwort pruefen."
            )
        token = None
        if isinstance(payload, dict):
            token = payload.get("tkn") or payload.get("token")
        if not token and headers.get("set-cookie"):
            token = _cookie_token(headers["set-cookie"])
        if not token:
            raise KickbaseAuthError(
                "Login-Antwort enthielt keinen Token (weder 'tkn' noch kkstrauth-Cookie)."
            )
        self._token = token
        expiry = None
        if isinstance(payload, dict):
            expiry = _parse_expiry(payload.get("tknex"))
        self._token_expiry = expiry or _jwt_expiry(token)
        return payload if isinstance(payload, dict) else {}

    def ensure_token(self) -> str:
        with self._lock:
            if not self._token_valid():
                self.login()
            assert self._token is not None
            return self._token

    # --------------------------------------------------------------- Requests

    def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        wait = self._last_request_at + self.min_interval - self._clock()
        if wait > 0:
            self._sleep(wait)
        self._last_request_at = self._clock()

    def _send(
        self,
        method: str,
        path: str,
        query: Mapping[str, Any] | None = None,
        body: Any = None,
        authenticated: bool = True,
    ) -> Response:
        url = self.base_url + path
        if query:
            clean = {k: v for k, v in query.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        headers = {
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        encoded = None
        if body is not None:
            encoded = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if authenticated:
            headers["Authorization"] = f"Bearer {self.ensure_token()}"
        self._throttle()
        return self._transport(method, url, headers, encoded, self.timeout)

    @staticmethod
    def _decode(raw: bytes, path: str) -> Any:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except ValueError:
            text = raw.decode("utf-8", "replace")
            raise KickbaseHTTPError(200, path, f"Keine gueltige JSON-Antwort: {text}")

    def request(
        self,
        method: str,
        path: str,
        query: Mapping[str, Any] | None = None,
        body: Any = None,
    ) -> Any:
        """Fuehrt einen API-Aufruf aus und gibt die geparste Antwort zurueck."""
        status, _, raw = self._send(method, path, query=query, body=body)
        if status == 401:
            # Token abgelaufen oder serverseitig invalidiert: einmal neu anmelden.
            with self._lock:
                self._token = None
                self._token_expiry = None
            status, _, raw = self._send(method, path, query=query, body=body)
            if status == 401:
                raise KickbaseAuthError(
                    "Kickbase hat den Token abgelehnt (HTTP 401). "
                    "Bitte Zugangsdaten pruefen."
                )
        if status >= 400:
            raise KickbaseHTTPError(status, path, raw.decode("utf-8", "replace"))
        return self._decode(raw, path)

    def get(self, path: str, **query: Any) -> Any:
        return self.request("GET", path, query=query)

    def post(self, path: str, body: Any = None, **query: Any) -> Any:
        return self.request("POST", path, query=query, body=body)

    def delete(self, path: str, body: Any = None, **query: Any) -> Any:
        return self.request("DELETE", path, query=query, body=body)
