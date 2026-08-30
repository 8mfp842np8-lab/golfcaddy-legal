"""MCP-Server (JSON-RPC 2.0 ueber stdio) fuer die Kickbase-API."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, IO, Mapping

from .client import KickbaseClient
from .errors import KickbaseError
from .glossary import legend_for
from .tools import REGISTRY, available_tools

SERVER_NAME = "kickbase"
SERVER_VERSION = "1.0.0"
DEFAULT_PROTOCOL = "2025-06-18"
SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18"}

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on", "ja"}


class KickbaseMCPServer:
    def __init__(
        self,
        client: KickbaseClient | None = None,
        allow_writes: bool = False,
        env: Mapping[str, str] | None = None,
    ) -> None:
        env = os.environ if env is None else env
        self.client = client or KickbaseClient.from_env(env)
        self.allow_writes = allow_writes or _truthy(env.get("KICKBASE_ENABLE_WRITES"))
        self.max_response_chars = int(env.get("KICKBASE_MAX_RESPONSE_CHARS") or 60000)

    # ------------------------------------------------------------- Dispatch

    def handle(self, message: Mapping[str, Any]) -> dict[str, Any] | None:
        """Verarbeitet eine Nachricht; ``None`` bedeutet: keine Antwort senden."""
        method = message.get("method")
        message_id = message.get("id")
        if not isinstance(method, str):
            if message_id is None:
                return None
            return _error(message_id, INVALID_REQUEST, "Feld 'method' fehlt.")

        # Notifications tragen keine id und werden nie beantwortet.
        is_notification = "id" not in message
        try:
            result = self._dispatch(method, message.get("params") or {})
        except KickbaseError as exc:
            if is_notification:
                return None
            return _error(message_id, INTERNAL_ERROR, str(exc))
        except _RpcError as exc:
            if is_notification:
                return None
            return _error(message_id, exc.code, exc.message)
        except Exception as exc:  # pragma: no cover - Schutznetz
            if is_notification:
                return None
            return _error(message_id, INTERNAL_ERROR, f"Interner Fehler: {exc}")

        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": message_id, "result": result}

    def _dispatch(self, method: str, params: Mapping[str, Any]) -> Any:
        if method == "initialize":
            return self._initialize(params)
        if method in ("notifications/initialized", "initialized"):
            return {}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {
                "tools": [t.spec() for t in available_tools(self.allow_writes)]
            }
        if method == "tools/call":
            return self._call_tool(params)
        if method in ("resources/list", "prompts/list"):
            # Der Server bietet nur Tools an; leere Listen halten Clients ruhig.
            return {"resources": []} if method == "resources/list" else {"prompts": []}
        raise _RpcError(METHOD_NOT_FOUND, f"Unbekannte Methode: {method}")

    def _initialize(self, params: Mapping[str, Any]) -> dict[str, Any]:
        requested = params.get("protocolVersion")
        version = (
            requested if requested in SUPPORTED_PROTOCOLS else DEFAULT_PROTOCOL
        )
        return {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": (
                "Zugriff auf Kickbase (inoffizielle API v4). Zuerst "
                "'kickbase_leagues' aufrufen, um die league_id zu erhalten. "
                "Feldabkuerzungen erklaert 'kickbase_glossary'."
            ),
        }

    # ---------------------------------------------------------------- Tools

    def _call_tool(self, params: Mapping[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            raise _RpcError(INVALID_PARAMS, "Feld 'name' fehlt.")
        if not isinstance(arguments, dict):
            raise _RpcError(INVALID_PARAMS, "'arguments' muss ein Objekt sein.")

        tool = REGISTRY.get(name)
        if tool is None:
            raise _RpcError(INVALID_PARAMS, f"Unbekanntes Tool: {name}")
        if tool.writes and not self.allow_writes:
            return _tool_error(
                f"Das Tool '{name}' veraendert deinen Kickbase-Account und ist "
                "deaktiviert. Setze KICKBASE_ENABLE_WRITES=1 in der MCP-"
                "Konfiguration, um schreibende Tools freizuschalten."
            )

        missing = [key for key in tool.schema["required"] if key not in arguments]
        if missing:
            return _tool_error(
                f"Pflichtfelder fehlen: {', '.join(missing)}."
            )

        if not self.client.has_credentials:
            return _tool_error(
                "Keine Kickbase-Zugangsdaten konfiguriert. Setze KICKBASE_EMAIL "
                "und KICKBASE_PASSWORD (oder KICKBASE_TOKEN) in der MCP-Konfiguration."
            )

        try:
            payload = tool.handler(self.client, arguments)
        except KickbaseError as exc:
            return _tool_error(str(exc))

        return {"content": [{"type": "text", "text": self._render(payload)}]}

    def _render(self, payload: Any) -> str:
        legend = legend_for(payload)
        document: Any = payload
        if legend:
            document = {"daten": payload, "_legende": legend}
        text = json.dumps(document, ensure_ascii=False, indent=2)
        if len(text) > self.max_response_chars:
            text = (
                text[: self.max_response_chars]
                + "\n... [Antwort gekuerzt; Abfrage weiter eingrenzen]"
            )
        return text

    # ----------------------------------------------------------- Hauptloop

    def serve(self, stdin: IO[str], stdout: IO[str]) -> None:
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                _write(stdout, _error(None, PARSE_ERROR, "Ungueltiges JSON."))
                continue
            if isinstance(message, list):
                # Batches: jede Nachricht einzeln beantworten.
                for item in message:
                    if isinstance(item, dict):
                        response = self.handle(item)
                        if response is not None:
                            _write(stdout, response)
                continue
            if not isinstance(message, dict):
                _write(stdout, _error(None, INVALID_REQUEST, "Erwartet wird ein Objekt."))
                continue
            response = self.handle(message)
            if response is not None:
                _write(stdout, response)


class _RpcError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }


def _tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def _write(stdout: IO[str], payload: Mapping[str, Any]) -> None:
    stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    stdout.flush()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--version" in argv:
        print(f"{SERVER_NAME} {SERVER_VERSION}")
        return 0
    server = KickbaseMCPServer()
    if not server.client.has_credentials:
        print(
            "Warnung: KICKBASE_EMAIL/KICKBASE_PASSWORD (oder KICKBASE_TOKEN) "
            "sind nicht gesetzt. Der Server startet, Tool-Aufrufe schlagen fehl.",
            file=sys.stderr,
        )
    try:
        server.serve(sys.stdin, sys.stdout)
    except (KeyboardInterrupt, BrokenPipeError):
        return 0
    return 0
