import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

from date_utils import to_iso_date  # noqa: E402


class ToIsoDateTest(unittest.TestCase):
    def test_day_first_dates(self):
        self.assertEqual(to_iso_date("30/09/2026"), "2026-09-30")
        self.assertEqual(to_iso_date("8/6/2026"), "2026-06-08")

    def test_iso_dates_and_datetimes(self):
        self.assertEqual(to_iso_date("2026-09-30"), "2026-09-30")
        self.assertEqual(to_iso_date("2026-09-30T10:15:00"), "2026-09-30")

    def test_unparseable_values_are_kept(self):
        self.assertEqual(to_iso_date("Desconeguda"), "Desconeguda")
        self.assertEqual(to_iso_date(None), "")

    def test_iso_sorts_chronologically_as_text(self):
        # The bug: '31/10/2017' > '30/09/2026' as text.
        self.assertGreater(to_iso_date("30/09/2026"), to_iso_date("31/10/2017"))


if __name__ == "__main__":
    unittest.main()
