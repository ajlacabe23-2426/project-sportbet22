"""Ingestion validation and chronological evaluation tests."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sportprob.evaluate import backtest
from sportprob.ingest import load_game_logs


DATA = Path(__file__).resolve().parents[1] / "data" / "demo_games.csv"


class PipelineTests(unittest.TestCase):
    def test_fixture_is_explicitly_synthetic(self):
        logs = load_game_logs(DATA)
        self.assertEqual(len(logs), 20)
        self.assertEqual({r.player_id for r in logs}, {"DEMO-001"})
        self.assertTrue(all(r.game_id.startswith("SYN-") for r in logs))

    def test_backtest_synthetic(self):
        logs = load_game_logs(DATA)
        evaluation = backtest(logs, "DEMO-001", "points")
        self.assertEqual(evaluation.evaluated_games, 15)
        self.assertTrue(0 <= evaluation.coverage_80 <= 1)
        self.assertTrue(0 <= evaluation.coverage_90 <= 1)
        self.assertGreaterEqual(evaluation.average_width_80, 0)
        self.assertGreaterEqual(evaluation.mean_negative_log_likelihood, 0)

    def test_duplicate_is_rejected(self):
        raw = DATA.read_text()
        duplicate = raw.splitlines()[1]
        with TemporaryDirectory() as folder:
            path = Path(folder) / "dupe.csv"
            path.write_text(raw + duplicate + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate game"):
                load_game_logs(path)

    def test_missing_required_column_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            path.write_text("game_id,player_id\nA,B\n")
            with self.assertRaisesRegex(ValueError, "missing CSV columns"):
                load_game_logs(path)


if __name__ == "__main__":
    unittest.main()
