import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import scraper  # noqa: E402

SELECT_HTML = """
<select class="form-control" id="_votaciones_legislatura" name="_votaciones_">
<option class="" selected value="16">

XVI Legislatura (2026-Actualidad)</option>
<option class="" value="15">

XV Legislatura (2023-2026)</option>
<option class="" value="10">

X Legislatura (2011-2016)</option>
</select>
<script>var diasVotaciones = [20260930,20260929, 20260915];</script>
"""


def touch(directory, name):
    with open(os.path.join(directory, name), "w", encoding="utf-8") as f:
        f.write("{}")


class ParsingTest(unittest.TestCase):
    def test_roman_to_int(self):
        self.assertEqual(scraper.roman_to_int("XIV"), 14)
        self.assertEqual(scraper.roman_to_int("XVI"), 16)
        self.assertEqual(scraper.roman_to_int("IX"), 9)

    def test_parse_legislatures_discovers_new_ones_in_order(self):
        self.assertEqual(scraper.parse_legislatures(SELECT_HTML), ["X", "XV", "XVI"])

    def test_parse_legislatures_without_selector(self):
        self.assertEqual(scraper.parse_legislatures("<html></html>"), [])

    def test_parse_voting_dates_sorted(self):
        self.assertEqual(scraper.parse_voting_dates(SELECT_HTML), [20260915, 20260929, 20260930])

    def test_raw_filename(self):
        url = "https://www.congreso.es/webpublica/opendata/votaciones/Leg15/Sesion202/20260930/Votacion001/VOT_1.json"
        self.assertEqual(scraper.raw_filename(url, 20260930, "XV"), "LXV_20260930_S202_V001.json")


class StateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raw = os.path.join(self.tmp.name, "raw")
        self.state = os.path.join(self.tmp.name, "state")
        os.makedirs(self.raw)
        os.makedirs(self.state)

    def tearDown(self):
        self.tmp.cleanup()

    def test_raw_counts_only_for_legislature(self):
        touch(self.raw, "LXV_20260930_S202_V001.json")
        touch(self.raw, "LXV_20260930_S202_V002.json")
        touch(self.raw, "LXIV_20230518_S100_V001.json")
        counts = scraper.raw_counts_by_date("XV", self.raw)
        self.assertEqual(counts, {20260930: 2})

    def test_pending_dates_detects_missing_and_partial_downloads(self):
        manifest = {20260915: 3, 20260929: 2}
        raw_counts = {20260915: 3, 20260929: 1}
        pending = scraper.pending_dates([20260915, 20260929, 20260930], manifest, raw_counts)
        self.assertEqual(pending, [20260929, 20260930])

    def test_lost_raw_files_make_dates_pending_again(self):
        # Regression: state said "done up to X" while data/raw was empty, so
        # nothing was re-downloaded and the transform published a stub dataset.
        manifest = {20260915: 3, 20260929: 2}
        self.assertEqual(scraper.pending_dates([20260915, 20260929], manifest, {}), [20260915, 20260929])

    def test_legacy_state_migration_trusts_only_dates_on_disk(self):
        with open(scraper.legacy_state_file("XV", self.state), "w", encoding="utf-8") as f:
            f.write("20260929")
        raw_counts = {20260915: 3, 20260930: 1}
        manifest = scraper.load_manifest("XV", raw_counts, self.state)
        # 20260929 has no files -> not trusted; 20260930 is after last fetch.
        self.assertEqual(manifest, {20260915: 3})

    def test_manifest_roundtrip(self):
        scraper.save_manifest("XV", {20260930: 21, 20260915: 3}, self.state)
        self.assertEqual(scraper.load_manifest("XV", {}, self.state), {20260915: 3, 20260930: 21})

    def test_recent_dates_are_not_settled(self):
        now = datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)
        self.assertTrue(scraper.is_settled(20260929, now))
        self.assertFalse(scraper.is_settled(20260930, now))
        self.assertFalse(scraper.is_settled(20261001, now))


if __name__ == "__main__":
    unittest.main()
