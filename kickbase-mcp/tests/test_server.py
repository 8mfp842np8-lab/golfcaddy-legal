import io
import json
import unittest

from kickbase_mcp.server import KickbaseMCPServer
from tests.fakes import FakeTransport, make_client


def _server(transport: FakeTransport, allow_writes: bool = False) -> KickbaseMCPServer:
    transport.add("POST", "/v4/user/login", {"tkn": "T1"})
    return KickbaseMCPServer(
        client=make_client(transport), allow_writes=allow_writes, env={}
    )


def _call(server: KickbaseMCPServer, name: str, arguments: dict) -> dict:
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    return response["result"]


def _payload(result: dict):
    return json.loads(result["content"][0]["text"])


class HandshakeTests(unittest.TestCase):
    def setUp(self):
        self.server = _server(FakeTransport())

    def test_initialize_spiegelt_bekannte_version(self):
        result = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            }
        )["result"]
        self.assertEqual(result["protocolVersion"], "2024-11-05")
        self.assertEqual(result["serverInfo"]["name"], "kickbase")
        self.assertIn("tools", result["capabilities"])

    def test_initialize_faellt_auf_default_zurueck(self):
        result = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "1999-01-01"},
            }
        )["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")

    def test_notification_bleibt_unbeantwortet(self):
        self.assertIsNone(
            self.server.handle(
                {"jsonrpc": "2.0", "method": "notifications/initialized"}
            )
        )

    def test_ping(self):
        self.assertEqual(
            self.server.handle({"jsonrpc": "2.0", "id": 9, "method": "ping"})["result"],
            {},
        )

    def test_unbekannte_methode(self):
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 3, "method": "gibtsnicht"}
        )
        self.assertEqual(response["error"]["code"], -32601)


class ToolListTests(unittest.TestCase):
    def test_schreibtools_sind_standardmaessig_versteckt(self):
        server = _server(FakeTransport())
        names = {
            t["name"]
            for t in server.handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            )["result"]["tools"]
        }
        self.assertIn("kickbase_squad", names)
        self.assertNotIn("kickbase_make_offer", names)

    def test_schreibtools_mit_flag_sichtbar(self):
        server = _server(FakeTransport(), allow_writes=True)
        names = {
            t["name"]
            for t in server.handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            )["result"]["tools"]
        }
        self.assertIn("kickbase_make_offer", names)

    def test_jedes_tool_hat_gueltiges_schema(self):
        server = _server(FakeTransport(), allow_writes=True)
        tools = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[
            "result"
        ]["tools"]
        self.assertGreater(len(tools), 10)
        for spec in tools:
            self.assertTrue(spec["description"])
            schema = spec["inputSchema"]
            self.assertEqual(schema["type"], "object")
            for key in schema["required"]:
                self.assertIn(key, schema["properties"])

    def test_env_flag_schaltet_schreibtools_frei(self):
        transport = FakeTransport()
        transport.add("POST", "/v4/user/login", {"tkn": "T1"})
        server = KickbaseMCPServer(
            client=make_client(transport), env={"KICKBASE_ENABLE_WRITES": "1"}
        )
        self.assertTrue(server.allow_writes)


class ToolCallTests(unittest.TestCase):
    def test_squad_liefert_daten_und_legende(self):
        transport = FakeTransport()
        transport.add(
            "GET",
            "/v4/leagues/7/squad",
            {"it": [{"pn": "Musiala", "mv": 30000000, "pos": 3}]},
        )
        server = _server(transport)
        payload = _payload(_call(server, "kickbase_squad", {"league_id": "7"}))
        self.assertEqual(payload["daten"]["it"][0]["pn"], "Musiala")
        self.assertIn("mv", payload["_legende"])
        self.assertIn("Marktwert", payload["_legende"]["mv"])

    def test_ranking_reicht_spieltag_durch(self):
        transport = FakeTransport()
        transport.add("GET", "/v4/leagues/7/ranking", {"us": []})
        server = _server(transport)
        _call(server, "kickbase_ranking", {"league_id": "7", "matchday": 5})
        self.assertEqual(transport.calls[-1]["query"], "dayNumber=5")

    def test_budget_buendelt_zwei_aufrufe(self):
        transport = FakeTransport()
        transport.add("GET", "/v4/leagues/7/me/budget", {"b": 1000})
        transport.add("GET", "/v4/leagues/7/me", {"tv": 200})
        server = _server(transport)
        payload = _payload(_call(server, "kickbase_budget", {"league_id": "7"}))
        self.assertEqual(payload["daten"]["budget"]["b"], 1000)
        self.assertEqual(payload["daten"]["me"]["tv"], 200)

    def test_suche_setzt_query_parameter(self):
        transport = FakeTransport()
        transport.add("GET", "/v4/competitions/1/players/search", {"it": []})
        server = _server(transport)
        _call(server, "kickbase_search_players", {"query": "Kane", "limit": 5})
        self.assertIn("query=Kane", transport.calls[-1]["query"])
        self.assertIn("max=5", transport.calls[-1]["query"])

    def test_fehlendes_pflichtfeld(self):
        server = _server(FakeTransport())
        result = _call(server, "kickbase_squad", {})
        self.assertTrue(result["isError"])
        self.assertIn("league_id", result["content"][0]["text"])

    def test_unbekanntes_tool(self):
        server = _server(FakeTransport())
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "kickbase_quatsch", "arguments": {}},
            }
        )
        self.assertEqual(response["error"]["code"], -32602)

    def test_schreibtool_ohne_flag_blockiert(self):
        transport = FakeTransport()
        server = _server(transport)
        result = _call(
            server,
            "kickbase_make_offer",
            {"league_id": "7", "player_id": "3", "price": 1000},
        )
        self.assertTrue(result["isError"])
        self.assertIn("KICKBASE_ENABLE_WRITES", result["content"][0]["text"])
        self.assertEqual(transport.calls, [])

    def test_schreibtool_mit_flag_sendet_request(self):
        transport = FakeTransport()
        transport.add("POST", "/v4/leagues/7/market/3/offers", {"ok": True})
        server = _server(transport, allow_writes=True)
        _call(
            server,
            "kickbase_make_offer",
            {"league_id": "7", "player_id": "3", "price": 1500000},
        )
        self.assertEqual(transport.calls[-1]["body"], {"price": 1500000})

    def test_raw_get_lehnt_fremde_pfade_ab(self):
        server = _server(FakeTransport())
        result = _call(server, "kickbase_raw_get", {"path": "/v3/user/me"})
        self.assertTrue(result["isError"])

    def test_raw_get_erlaubt_v4(self):
        transport = FakeTransport()
        transport.add("GET", "/v4/base/overview", {"ok": 1})
        server = _server(transport)
        result = _call(server, "kickbase_raw_get", {"path": "/v4/base/overview"})
        self.assertNotIn("isError", result)

    def test_api_fehler_wird_als_toolfehler_gemeldet(self):
        transport = FakeTransport()
        transport.add("GET", "/v4/leagues/7/squad", {"err": "boom"}, status=500)
        server = _server(transport)
        result = _call(server, "kickbase_squad", {"league_id": "7"})
        self.assertTrue(result["isError"])
        self.assertIn("500", result["content"][0]["text"])

    def test_ohne_zugangsdaten_klare_meldung(self):
        from kickbase_mcp.client import KickbaseClient

        server = KickbaseMCPServer(
            client=KickbaseClient(transport=FakeTransport(), min_interval=0), env={}
        )
        result = _call(server, "kickbase_squad", {"league_id": "7"})
        self.assertTrue(result["isError"])
        self.assertIn("KICKBASE_EMAIL", result["content"][0]["text"])

    def test_lange_antwort_wird_gekuerzt(self):
        transport = FakeTransport()
        transport.add("GET", "/v4/leagues/7/squad", {"it": ["x" * 100] * 200})
        server = _server(transport)
        server.max_response_chars = 500
        text = _call(server, "kickbase_squad", {"league_id": "7"})["content"][0]["text"]
        self.assertIn("gekuerzt", text)


class StdioTests(unittest.TestCase):
    def test_serve_beantwortet_zeilenweise(self):
        server = _server(FakeTransport())
        stdin = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            + "\n"
            + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
            + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            + "\n"
        )
        stdout = io.StringIO()
        server.serve(stdin, stdout)
        lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual([line["id"] for line in lines], [1, 2])

    def test_ungueltiges_json_meldet_parse_error(self):
        server = _server(FakeTransport())
        stdout = io.StringIO()
        server.serve(io.StringIO("kein json\n"), stdout)
        self.assertEqual(
            json.loads(stdout.getvalue())["error"]["code"], -32700
        )


if __name__ == "__main__":
    unittest.main()
