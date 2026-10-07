import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import build_home_extras as bhe  # noqa: E402

GRUPOS = ["GMx", "GP", "GS"]
MX, PP, PS = 0, 1, 2


def vote(vid, leg, fecha, tags=()):
    return {"id": vid, "legislatura": leg, "fecha": fecha, "titulo_ciudadano": f"Votación {vid}",
            "categoria": 0, "etiquetas": list(tags)}


def result(favor, contra, abst=0):
    return {"favor": favor, "contra": contra, "abstencion": abst, "total": favor + contra + abst,
            "result": "Aprobada" if favor > contra else "Rechazada", "margin": abs(favor - contra)}


def ballots(vot_idx, pp, ps, mx=()):
    """Rows for one vote: each list holds the vote codes of that group's members."""
    rows = []
    for grupo, codes in ((PP, pp), (PS, ps), (MX, mx)):
        rows.extend([vot_idx, len(rows) + k, grupo, code] for k, code in enumerate(codes))
    return rows


class ScopeFixture:
    def __init__(self, votaciones, results, votos_by_leg, featured=(), detail_by_leg=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.write("votaciones_meta.json", {"votaciones": votaciones, "votResults": results, "grupos": GRUPOS})
        self.write("manifest_home.json", {"featuredVotes": [{"id": f} for f in featured]})
        for leg, rows in votos_by_leg.items():
            self.write(f"votos_{leg}.json", {"votos": rows, "detail": (detail_by_leg or {}).get(leg, {})})

    def write(self, name, payload):
        with open(os.path.join(self.dir, name), "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def build(self):
        return bhe.build_scope(self.dir, bhe.BASE_HIDDEN_TAGS)

    def close(self):
        self.tmp.cleanup()


class ParseDateTest(unittest.TestCase):
    def test_accepts_iso_and_regional_formats(self):
        self.assertEqual(bhe.parse_date("2024-03-01"), date(2024, 3, 1))
        self.assertEqual(bhe.parse_date("1/3/2024"), date(2024, 3, 1))
        self.assertIsNone(bhe.parse_date("ayer"))


class BuildScopeTest(unittest.TestCase):
    def fixture(self, *args, **kwargs):
        fx = ScopeFixture(*args, **kwargs)
        self.addCleanup(fx.close)
        return fx

    def test_current_legislature_uses_real_dates_not_text_order(self):
        # As text, "31/12/2019" sorts after "01/02/2024".
        fx = self.fixture(
            [vote("a", "I", "31/12/2019"), vote("b", "II", "01/02/2024")],
            [result(3, 1), result(3, 1)],
            {"I": ballots(0, [1, 1], [2]), "II": ballots(1, [1, 1], [2])},
        )
        self.assertEqual(fx.build()["legislatura"], "II")

    def test_featured_votes_carry_group_tallies_and_summary(self):
        fx = self.fixture(
            [vote("old", "I", "2019-05-01"), vote("new", "II", "2024-05-01")],
            [result(2, 2, 1), result(4, 0)],
            {"I": ballots(0, [1, 1], [2, 2], [3]), "II": ballots(1, [1, 1], [1, 1])},
            featured=["old"],
            detail_by_leg={"I": {"0": {"resumen": "Votar a favor significa X."}}},
        )
        [spot] = fx.build()["spotlight"]
        self.assertEqual(spot["id"], "old")
        self.assertEqual(spot["resumen"], "Votar a favor significa X.")
        self.assertEqual(spot["groups"], {"GP": [2, 0, 0, 0], "GS": [0, 2, 0, 0], "GMx": [0, 0, 1, 0]})

    def test_without_featured_votes_spotlight_falls_back_to_contested_ones(self):
        fx = self.fixture(
            [vote("unanime", "II", "2024-05-02"), vote("reñida", "II", "2024-05-01")],
            [result(10, 0), result(6, 4)],
            {},  # No nominal votes, like Madrid or Catalunya.
        )
        spotlight = fx.build()["spotlight"]
        self.assertEqual([s["id"] for s in spotlight], ["reñida"])
        self.assertIsNone(spotlight[0]["groups"])

    def test_questions_tally_each_group_position_per_topic(self):
        dates = [f"2024-0{m}-01" for m in range(1, 7)]
        votaciones = [vote(f"v{i}", "II", d, ["subir_pensiones", "nacional"]) for i, d in enumerate(dates)]
        # PP votes for in all six; PSOE against in four and split in two.
        rows = []
        for i in range(6):
            ps = [2, 2] if i < 4 else [1, 2]
            rows += ballots(i, [1, 1], ps, [1])
        fx = self.fixture(votaciones, [result(3, 2)] * 6, {"II": rows})

        questions = fx.build()["questions"]
        self.assertEqual(questions["groups"], ["GP", "GS"])  # Mixto has no group line.
        [topic] = questions["topics"]  # "nacional" is not a topic.
        self.assertEqual(topic["tag"], "subir_pensiones")
        self.assertEqual(topic["tally"], {"GP": [6, 0, 0], "GS": [0, 4, 0]})
        recent = [questions["votes"][r] for r in topic["recent"]]
        self.assertEqual(recent[0]["id"], "v5")  # Most recent first.
        self.assertEqual(recent[0]["pos"], {"GP": 1})  # Split PSOE has no position.

    def test_home_example_topics_are_kept_beyond_the_top(self):
        common = [f"comun_{k}" for k in range(bhe.MAX_TOPICS)]
        votaciones = [vote(f"v{i}", "II", f"2024-01-{i + 1:02d}", [*common, "subir_pensiones"]) for i in range(6)]
        votaciones.append(vote("extra", "II", "2024-02-01", common))  # Common topics outnumber it.
        rows = [r for i in range(len(votaciones)) for r in ballots(i, [1], [2])]
        fx = self.fixture(votaciones, [result(1, 1)] * len(votaciones), {"II": rows})
        fx.write("manifest_home.json", {"heroExamples": [["subir_pensiones", "Pensiones"]]})

        tags = [t["tag"] for t in fx.build()["questions"]["topics"]]
        self.assertIn("subir_pensiones", tags)
        self.assertEqual(len(tags), bhe.MAX_TOPICS + 1)

    def test_topics_need_enough_votes(self):
        votaciones = [vote(f"v{i}", "II", f"2024-01-0{i + 1}", ["raro"]) for i in range(bhe.MIN_TOPIC_VOTES - 1)]
        rows = [r for i in range(len(votaciones)) for r in ballots(i, [1], [2])]
        fx = self.fixture(votaciones, [result(1, 1)] * len(votaciones), {"II": rows})
        self.assertEqual(fx.build()["questions"]["topics"], [])


if __name__ == "__main__":
    unittest.main()
