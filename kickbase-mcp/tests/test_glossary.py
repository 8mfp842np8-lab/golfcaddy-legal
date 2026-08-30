import unittest

from kickbase_mcp.glossary import legend_for


class LegendTests(unittest.TestCase):
    def test_findet_felder_verschachtelt(self):
        payload = {"it": [{"pn": "Kane", "stats": {"mv": 1, "unbekannt": 2}}]}
        legend = legend_for(payload)
        self.assertIn("pn", legend)
        self.assertIn("mv", legend)
        self.assertNotIn("unbekannt", legend)

    def test_leere_legende_bei_unbekannten_feldern(self):
        self.assertEqual(legend_for({"foo": "bar"}), {})

    def test_bricht_bei_tiefer_verschachtelung_ab(self):
        node: dict = {"mv": 1}
        for _ in range(50):
            node = {"child": node}
        self.assertEqual(legend_for(node), {})

    def test_vertraegt_skalare(self):
        self.assertEqual(legend_for(None), {})
        self.assertEqual(legend_for([1, "a"]), {})


if __name__ == "__main__":
    unittest.main()
