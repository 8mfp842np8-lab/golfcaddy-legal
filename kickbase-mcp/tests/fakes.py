"""Test-Doubles: ein HTTP-Transport ohne echte Netzwerkzugriffe."""

from __future__ import annotations

import json
from typing import Any

from kickbase_mcp.client import KickbaseClient


class FakeTransport:
    """Beantwortet Requests aus einer vorbereiteten Routen-Tabelle."""

    def __init__(self, routes: dict[tuple[str, str], Any] | None = None) -> None:
        # Schluessel: (METHOD, pfad-ohne-query) -> (status, headers, payload)
        self.routes = routes or {}
        self.calls: list[dict[str, Any]] = []

    def add(
        self,
        method: str,
        path: str,
        payload: Any,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.routes[(method.upper(), path)] = (status, headers or {}, payload)

    def __call__(self, method, url, headers, body, timeout):
        path = url.split("://", 1)[-1].split("/", 1)[1]
        path = "/" + path
        bare, _, query = path.partition("?")
        self.calls.append(
            {
                "method": method,
                "path": bare,
                "query": query,
                "headers": headers,
                "body": json.loads(body) if body else None,
            }
        )
        key = (method.upper(), bare)
        if key not in self.routes:
            return (404, {}, json.dumps({"err": f"keine Route fuer {key}"}).encode())
        status, response_headers, payload = self.routes[key]
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return (status, response_headers, raw)


def make_client(transport: FakeTransport, **kwargs: Any) -> KickbaseClient:
    params: dict[str, Any] = {
        "email": "manager@example.com",
        "password": "geheim",
        "transport": transport,
        "min_interval": 0,
    }
    params.update(kwargs)
    return KickbaseClient(**params)
