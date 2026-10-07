import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import transform  # noqa: E402


def raw_vote(fecha, sesion, numero, votos, totales=None, texto="Texto"):
    return {
        "informacion": {
            "sesion": sesion,
            "numeroVotacion": numero,
            "fecha": fecha,
            "titulo": "Titulo",
            "textoExpediente": texto,
            "tituloSubGrupo": "",
            "textoSubGrupo": "",
        },
        "totales": totales or {"asentimiento": "No"},
        "votaciones": [{"diputado": d, "grupo": g, "voto": v} for d, g, v in votos],
    }


class PureFunctionsTest(unittest.TestCase):
    def test_tally_nominal_votes(self):
        counts, entries, asentimiento = transform.tally_votes(
            raw_vote("1/1/2026", 1, 1, [("A", "GP", "Sí"), ("B", "GS", "No"), ("C", "GS", "No vota")])
        )
        self.assertEqual(counts, {"favor": 1, "contra": 1, "abstencion": 0, "no_vota": 1})
        self.assertEqual(len(entries), 3)
        self.assertFalse(asentimiento)

    def test_assent_vote_is_approved(self):
        data = raw_vote("1/1/2026", 1, 1, [], {"asentimiento": "Sí", "afavor": 0, "enContra": 0})
        counts, entries, asentimiento = transform.tally_votes(data)
        self.assertTrue(asentimiento)
        self.assertEqual(entries, [])
        self.assertEqual(transform.vote_result(counts["favor"], counts["contra"], asentimiento), "Aprobada")

    def test_secret_ballot_uses_official_totals(self):
        totales = {"asentimiento": "No", "afavor": 146, "enContra": 184, "abstenciones": 2, "noVotan": 18}
        counts, _, asentimiento = transform.tally_votes(raw_vote("1/8/2013", 124, 2, [], totales))
        self.assertEqual((counts["favor"], counts["contra"], counts["abstencion"]), (146, 184, 2))
        self.assertEqual(transform.vote_result(counts["favor"], counts["contra"], asentimiento), "Rechazada")

    def test_group_majority_ignores_fully_absent_groups(self):
        gm = transform.group_majorities({"GP": {1: 3, 2: 0, 3: 0, 4: 1}, "GV": {1: 0, 2: 0, 3: 0, 4: 5}})
        self.assertEqual(gm, {"GP": 1})

    def test_group_without_absolute_majority_has_no_position(self):
        gm = transform.group_majorities({"GMx": {1: 4, 2: 4, 3: 0, 4: 0}, "GS": {1: 0, 2: 3, 3: 2, 4: 0}})
        self.assertEqual(gm, {"GS": 2})

    def test_non_partisan_groups(self):
        for name in ("GMx", "Grupo Mixto", "GPlu", "No Adscrito", "no adscrita"):
            self.assertTrue(transform.is_non_partisan_group(name), name)
        self.assertFalse(transform.is_non_partisan_group("GP"))

    def test_classify_subgrupo(self):
        cases = {
            "": "",
            "Votación de conjunto": "final",
            "Texto del dictamen de la Sección 12": "final",
            "Enmiendas a la totalidad de texto alternativo": "totalidad",
            "Enmiendas transaccionales.": "transaccional",
            "Votación separada por puntos": "separada",
            "Enmiendas del Grupo Parlamentario Vasco": "enmienda",
            "Propuestas de resolución presentadas por el Grupo Parlamentario Popular": "propuesta",
            "GP Mixto (ERC)": "otro",
        }
        for title, expected in cases.items():
            self.assertEqual(transform.classify_subgrupo(title), expected, title)

    def test_find_shrinkage(self):
        self.assertEqual(transform.find_shrinkage({"XIV": 10, "XV": 5}, {"XV": 7}), {"XIV": (10, 0)})
        self.assertEqual(transform.find_shrinkage({"XV": 5}, {"XV": 5, "XVI": 1}), {})

    def test_raw_files_sort_chronologically(self):
        names = ["LX_20150101_S1_V1.json", "LXV_20260101_S2_V10.json", "LXV_20260101_S2_V9.json", "LXIV_20200101_S1_V1.json"]
        self.assertEqual(
            sorted(names, key=transform.raw_file_sort_key),
            ["LX_20150101_S1_V1.json", "LXIV_20200101_S1_V1.json", "LXV_20260101_S2_V9.json", "LXV_20260101_S2_V10.json"],
        )

    def test_get_leg_after_dissolution(self):
        self.assertEqual(transform.get_leg("2026-11-15"), "XV")
        self.assertEqual(transform.get_leg("2027-01-10"), "XVI")


class TransformMainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.raw = os.path.join(root, "raw")
        self.public = os.path.join(root, "public")
        os.makedirs(self.raw)
        os.makedirs(self.public)
        with open(os.path.join(self.public, "ambitos.json"), "w", encoding="utf-8") as f:
            json.dump({"ambitos": [{"id": "nacional", "legislaturas": ["XV"]}]}, f)
        self.patcher = mock.patch.multiple(
            transform,
            RAW_DIR=self.raw,
            PUBLIC_DIR=self.public,
            META_FILE=os.path.join(self.public, "votaciones_meta.json"),
            MANIFEST_FILE=os.path.join(self.public, "manifest_home.json"),
            AMBITOS_FILE=os.path.join(self.public, "ambitos.json"),
            CACHE_FILE=os.path.join(root, "cache.json"),
            FOTO_MAP_FILE=os.path.join(root, "missing.json"),
            PROVINCIA_MAP_FILE=os.path.join(root, "missing.json"),
            FEATURED_FILE=os.path.join(root, "missing.json"),
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def write_raw(self, name, payload):
        with open(os.path.join(self.raw, name), "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def run_main(self, *args):
        with mock.patch.object(sys, "argv", ["transform.py", "--skip-ai", *args]):
            transform.main()

    def read(self, name):
        with open(os.path.join(self.public, name), encoding="utf-8") as f:
            return json.load(f)

    def seed_two_legislatures(self):
        self.write_raw(
            "LXIV_20200210_S10_V1.json",
            raw_vote("10/2/2020", 10, 1, [("Ana", "GCs", "Sí"), ("Bea", "GS", "No")]),
        )
        self.write_raw(
            "LXV_20240210_S20_V1.json",
            raw_vote("10/2/2024", 20, 1, [("Ana", "GP", "No"), ("Bea", "GS", "No")]),
        )

    def test_outputs_current_group_and_recent_legislature_first(self):
        self.seed_two_legislatures()
        self.run_main()
        meta = self.read("votaciones_meta.json")
        ana = meta["diputados"].index("Ana")
        self.assertEqual(meta["grupos"][meta["dipStats"][ana]["mainGrupo"]], "GP")
        self.assertEqual(meta["dipStats"][ana]["legislaturas"], ["XV", "XIV"])
        self.assertEqual(self.read("ambitos.json")["ambitos"][0]["legislaturas"], ["XV", "XIV"])

    def test_loyalty_not_measured_for_mixto(self):
        self.write_raw(
            "LXV_20240210_S20_V1.json",
            raw_vote("10/2/2024", 20, 1, [("Ana", "GMx", "Sí"), ("Bea", "GMx", "No"), ("Carla", "GP", "No"), ("Dani", "GP", "No"), ("Eva", "GP", "Sí")]),
        )
        self.run_main()
        meta = self.read("votaciones_meta.json")
        loyalty = {name: meta["dipStats"][i]["loyalty"] for i, name in enumerate(meta["diputados"])}
        self.assertIsNone(loyalty["Ana"])
        self.assertEqual(loyalty["Carla"], 1)
        self.assertEqual(loyalty["Eva"], 0)

    def test_refuses_to_publish_when_raw_is_incomplete(self):
        self.seed_two_legislatures()
        self.run_main()
        os.remove(os.path.join(self.raw, "LXIV_20200210_S10_V1.json"))
        with self.assertRaises(SystemExit) as ctx:
            self.run_main()
        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(len(self.read("votaciones_meta.json")["votaciones"]), 2)

    def test_allow_shrink_overrides_guard(self):
        self.seed_two_legislatures()
        self.run_main()
        os.remove(os.path.join(self.raw, "LXIV_20200210_S10_V1.json"))
        self.run_main("--allow-shrink")
        self.assertEqual(len(self.read("votaciones_meta.json")["votaciones"]), 1)

    def test_warns_about_uncategorized_votes(self):
        self.seed_two_legislatures()
        with mock.patch("builtins.print") as fake_print:
            self.run_main()
        warnings = [c.args[0] for c in fake_print.call_args_list if c.args and str(c.args[0]).startswith("::warning title=IA::")]
        self.assertEqual(len(warnings), 1)
        self.assertIn("2 votaciones sin categorizar (XIV: 1, XV: 1)", warnings[0])

    def test_fallback_titles_are_not_frozen_by_overrides(self):
        self.seed_two_legislatures()
        self.run_main()  # no AI -> placeholder titles
        with open(transform.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({transform.text_hash("Texto"): {"titulo_ciudadano": "Titulo IA", "categoria_principal": "Sanidad", "etiquetas": []}}, f)
        self.run_main()
        titles = {v["titulo_ciudadano"] for v in self.read("votaciones_meta.json")["votaciones"]}
        self.assertEqual(titles, {"Titulo IA"})


if __name__ == "__main__":
    unittest.main()
