"""Regression coverage for the offline three-stat research snapshot."""
from datetime import date
from pathlib import Path
from subprocess import run
import json
import os
import sys
import unittest

from sportprob.ingest import load_game_logs
from sportprob.performance_snapshot import build_player_snapshot
from sportprob.schema import GameLog

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "demo_games.csv"
MANIFEST = ROOT / "data" / "demo_games.manifest.json"


class PlayerSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logs = load_game_logs(DATA)

    def test_three_stats_share_point_in_time_cutoff(self):
        output = build_player_snapshot(self.logs, "DEMO-001", date(2025, 11, 21))
        self.assertEqual(set(output["stats"]), {"points", "rebounds", "assists"})
        self.assertEqual(output["schema"], "sportprob-player-tri-stat-snapshot-v1")
        self.assertEqual(output["limitations"]["wagering_or_order_execution"], False)
        self.assertEqual(output["limitations"]["independent_predictive_accuracy_verified"], False)
        self.assertLess(output["last_observed_game"], output["as_of_exclusive"])
        for result in output["stats"].values():
            self.assertGreaterEqual(result["projected_mean"], 0)
            self.assertLessEqual(result["model_interval_90"][0],
                                 result["model_interval_80"][0])
            self.assertGreaterEqual(result["model_interval_90"][1],
                                    result["model_interval_80"][1])

    def test_future_game_does_not_change_earlier_snapshot(self):
        cutoff = date(2025, 11, 21)
        baseline = build_player_snapshot(self.logs, "DEMO-001", cutoff)
        later = GameLog(
            game_id="NOT_YET", player_id="DEMO-001", game_date=date(2025, 12, 31),
            opponent="XXX", home=None, minutes=38, points=100, rebounds=90, assists=80
        )
        updated = build_player_snapshot(self.logs + [later], "DEMO-001", cutoff)
        self.assertEqual(baseline, updated)

    def test_insufficient_history_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "five completed games"):
            build_player_snapshot(self.logs, "DEMO-001", date(2025, 11, 3))

    def test_cli_uses_manifest_and_marks_synthetic(self):
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        proc = run(
            [sys.executable, "-m", "sportprob.performance_snapshot",
             "--data", str(DATA), "--manifest", str(MANIFEST),
             "--player", "DEMO-001", "--as-of", "2025-11-21"],
            capture_output=True, text=True, env=env, check=True
        )
        output = json.loads(proc.stdout)
        self.assertTrue(output["synthetic"])
        self.assertEqual(output["dataset_sha256"], json.loads(
            MANIFEST.read_text(encoding="utf-8"))["sha256"])
        self.assertEqual(output["as_of_exclusive"], "2025-11-21")


if __name__ == "__main__":
    unittest.main()
