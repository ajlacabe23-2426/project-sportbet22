"""Tests for the manual historical-statistics research workflow."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sportprob.manual_research import build_manual_research_report


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "demo_games.csv"
MANIFEST = ROOT / "data" / "demo_games.manifest.json"


class ManualResearchTests(unittest.TestCase):
    def test_checksum_gated_historical_report(self):
        report = build_manual_research_report(
            DATA, MANIFEST, date(2025, 11, 21), player_id="DEMO-001"
        )
        self.assertTrue(report["research_only"])
        self.assertFalse(report["future_prediction"])
        self.assertFalse(report["wagering_outputs"])
        self.assertTrue(report["dataset"]["synthetic"])
        self.assertEqual(len(report["players"]), 1)
        stats = report["players"][0]["statistics"]
        self.assertEqual(set(stats), {"points", "rebounds", "assists"})
        for record in stats.values():
            self.assertLess(record["last_game"], report["as_of_exclusive"])
            self.assertGreaterEqual(record["games_used"], 5)

    def test_earlier_cutoff_never_includes_future_dates(self):
        report = build_manual_research_report(
            DATA, MANIFEST, date(2025, 11, 15)
        )
        for player in report["players"]:
            for record in player["statistics"].values():
                self.assertLess(record["last_game"], "2025-11-15")

    def test_source_bytes_must_match_manifest(self):
        with TemporaryDirectory() as temporary:
            tampered = Path(temporary) / "tampered.csv"
            tampered.write_bytes(DATA.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                build_manual_research_report(
                    tampered, MANIFEST, date(2025, 11, 21)
                )

    def test_unknown_player_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "not present"):
            build_manual_research_report(
                DATA, MANIFEST, date(2025, 11, 21),
                player_id="MISSING-PLAYER"
            )

    def test_insufficient_history_is_not_fabricated(self):
        report = build_manual_research_report(
            DATA, MANIFEST, date(2025, 11, 2)
        )
        self.assertEqual(report["players"], [])
        self.assertEqual(len(report["insufficient_history"]), 1)

    def test_invalid_window_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "history_games"):
            build_manual_research_report(
                DATA, MANIFEST, date(2025, 11, 21),
                history_games=4
            )


if __name__ == "__main__":
    unittest.main()
