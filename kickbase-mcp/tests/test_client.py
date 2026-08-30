import json
import unittest

from kickbase_mcp.client import KickbaseClient, _cookie_token, _jwt_expiry, _parse_expiry
from kickbase_mcp.errors import KickbaseAuthError, KickbaseConfigError, KickbaseHTTPError
from tests.fakes import FakeTransport, make_client


def _token(exp: int) -> str:
    import base64

    def b64(data: dict) -> str:
        raw = json.dumps(data).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{b64({'alg': 'HS256'})}.{b64({'exp': exp})}.signatur"


class TokenHelperTests(unittest.TestCase):
    def test_jwt_expiry_liest_exp(self):
        self.assertEqual(_jwt_expiry(_token(1770973597)), 1770973597.0)

    def test_jwt_expiry_bei_unsinn_none(self):
        self.assertIsNone(_jwt_expiry("kein-jwt"))
        self.assertIsNone(_jwt_expiry("a.b.c"))

    def test_parse_expiry_iso(self):
        self.assertEqual(
            _parse_expiry("2026-02-13T09:06:37Z"),
            _parse_expiry(1770973597.0),
        )

    def test_cookie_token(self):
        header = (
            "kkstrauth=abc.def.ghi; expires=Fri, 13 Feb 2026 09:06:37 GMT; "
            "domain=.kickbase.com; path=/"
        )
        self.assertEqual(_cookie_token(header), "abc.def.ghi")

    def test_cookie_token_ohne_treffer(self):
        self.assertIsNone(_cookie_token("other=1; path=/"))


class LoginTests(unittest.TestCase):
    def test_login_nutzt_tkn_aus_body(self):
        transport = FakeTransport()
        transport.add("POST", "/v4/user/login", {"tkn": "T1", "u": {"i": "42"}})
        client = make_client(transport)
        client.login()
        self.assertEqual(client.ensure_token(), "T1")
        self.assertEqual(transport.calls[0]["body"]["em"], "manager@example.com")

    def test_login_faellt_auf_cookie_zurueck(self):
        transport = FakeTransport()
        transport.add(
            "POST",
            "/v4/user/login",
            {"u": {}},
            headers={"set-cookie": "kkstrauth=COOKIETOKEN; path=/"},
        )
        client = make_client(transport)
        client.login()
        self.assertEqual(client.ensure_token(), "COOKIETOKEN")

    def test_login_ohne_zugangsdaten(self):
        client = KickbaseClient(transport=FakeTransport(), min_interval=0)
        with self.assertRaises(KickbaseConfigError):
            client.login()
        self.assertFalse(client.has_credentials)

    def test_falsche_zugangsdaten(self):
        transport = FakeTransport()
        transport.add("POST", "/v4/user/login", {"err": 401}, status=401)
        client = make_client(transport)
        with self.assertRaises(KickbaseAuthError):
            client.login()

    def test_login_ohne_token_in_antwort(self):
        transport = FakeTransport()
        transport.add("POST", "/v4/user/login", {"u": {}})
        client = make_client(transport)
        with self.assertRaises(KickbaseAuthError):
            client.login()


class RequestTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()
        self.transport.add("POST", "/v4/user/login", {"tkn": "T1"})

    def test_get_setzt_bearer_header(self):
        self.transport.add("GET", "/v4/user/me", {"i": "42"})
        client = make_client(self.transport)
        self.assertEqual(client.get("/v4/user/me"), {"i": "42"})
        me_call = self.transport.calls[-1]
        self.assertEqual(me_call["headers"]["Authorization"], "Bearer T1")

    def test_query_ohne_none_werte(self):
        self.transport.add("GET", "/v4/leagues/7/ranking", {"it": []})
        client = make_client(self.transport)
        client.get("/v4/leagues/7/ranking", dayNumber=None)
        self.assertEqual(self.transport.calls[-1]["query"], "")

    def test_401_loest_erneuten_login_aus(self):
        calls = {"n": 0}
        transport = FakeTransport()
        transport.add("POST", "/v4/user/login", {"tkn": "T1"})

        def me(method, url, headers, body, timeout):
            calls["n"] += 1
            if calls["n"] == 1:
                return (401, {}, b"{}")
            return (200, {}, json.dumps({"i": "42"}).encode())

        transport.routes[("GET", "/v4/user/me")] = (200, {}, {"i": "42"})
        client = make_client(transport)
        original = transport.__call__

        def wrapper(method, url, headers, body, timeout):
            if url.endswith("/v4/user/me"):
                return me(method, url, headers, body, timeout)
            return original(method, url, headers, body, timeout)

        client._transport = wrapper
        self.assertEqual(client.get("/v4/user/me"), {"i": "42"})
        self.assertEqual(calls["n"], 2)

    def test_dauerhaftes_401_wirft(self):
        transport = FakeTransport()
        transport.add("POST", "/v4/user/login", {"tkn": "T1"})
        transport.add("GET", "/v4/user/me", {}, status=401)
        client = make_client(transport)
        with self.assertRaises(KickbaseAuthError):
            client.get("/v4/user/me")

    def test_http_fehler_wird_gemeldet(self):
        self.transport.add("GET", "/v4/leagues/7/squad", {"err": "nope"}, status=500)
        client = make_client(self.transport)
        with self.assertRaises(KickbaseHTTPError) as ctx:
            client.get("/v4/leagues/7/squad")
        self.assertEqual(ctx.exception.status, 500)

    def test_abgelaufener_token_erzwingt_login(self):
        self.transport.add("GET", "/v4/user/me", {"i": "42"})
        client = make_client(self.transport, token=_token(1000), clock=lambda: 5000.0)
        client.get("/v4/user/me")
        self.assertIn(
            "/v4/user/login", [call["path"] for call in self.transport.calls]
        )

    def test_gueltiger_token_spart_login(self):
        self.transport.add("GET", "/v4/user/me", {"i": "42"})
        client = make_client(self.transport, token=_token(9000), clock=lambda: 1000.0)
        client.get("/v4/user/me")
        self.assertNotIn(
            "/v4/user/login", [call["path"] for call in self.transport.calls]
        )


class ThrottleTests(unittest.TestCase):
    def test_min_interval_wartet(self):
        slept: list[float] = []
        now = {"t": 100.0}
        transport = FakeTransport()
        transport.add("POST", "/v4/user/login", {"tkn": "T1"})
        transport.add("GET", "/v4/user/me", {"i": "1"})
        client = make_client(
            transport,
            min_interval=0.5,
            clock=lambda: now["t"],
            sleep=slept.append,
        )
        client.get("/v4/user/me")
        client.get("/v4/user/me")
        self.assertTrue(any(value > 0 for value in slept))


class FromEnvTests(unittest.TestCase):
    def test_liest_umgebungsvariablen(self):
        client = KickbaseClient.from_env(
            {
                "KICKBASE_EMAIL": "a@b.de",
                "KICKBASE_PASSWORD": "pw",
                "KICKBASE_MIN_REQUEST_INTERVAL": "1.5",
            }
        )
        self.assertEqual(client.email, "a@b.de")
        self.assertEqual(client.min_interval, 1.5)
        self.assertTrue(client.has_credentials)

    def test_leere_umgebung(self):
        client = KickbaseClient.from_env({})
        self.assertFalse(client.has_credentials)


if __name__ == "__main__":
    unittest.main()
