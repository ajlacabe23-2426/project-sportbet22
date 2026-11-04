"""Retrospective, multi-player source and cutoff regression coverage."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from sportprob.cohort_audit import audit_cohort, audit_local_cohort
from sportprob.schema import GameLog


def synthetic_player(player_id, count=30, start=date(2025, 1, 1)):
    return [
        GameLog(
            game_id=f"{player_id}-G{i}", player_id=player_id,
            game_date=start + timedelta(days=i*2),
            opponent=f"EXAMPLE-{i%7}", home=bool(i%2),
            minutes=30.0, points=15+i%11,
            rebounds=3+i%5, assists=2+i%4,
        )
        for i in range(count)
    ]


class CohortAuditTests(unittest.TestCase):
    def test_two_players_evaluated_on_frozen_history_for_each_stat(self):
        logs = synthetic_player("A") + synthetic_player("B")
        cutoff = date(2025, 2, 10)  # 20 training games per player
        result = audit_cohort(logs, holdout_start=cutoff)
        self.assertEqual(result["player_count"], 2)
        self.assertEqual(result["eligible_player_count"], 2)
        self.assertFalse(result["future_outcomes_used_in_training"])
        self.assertFalse(result["independently_verified_model_accuracy"])
        for player in result["players"]:
            self.assertEqual(player["frozen_training_games"], 20)
            self.assertEqual(player["historical_holdout_games"], 10)
            self.assertEqual(set(player["stat_diagnostics"]), {"points", "rebounds", "assists"})
            for stat in player["stat_diagnostics"].values():
                self.assertEqual(stat["evaluated_games"], 10)
                self.assertEqual(stat["training_policy"], "frozen_pre_holdout_only")
                self.assertEqual(len(stat["scores"]), 2)

    def test_unavailable_player_sample_is_reported_not_fake_scored(self):
        records = synthetic_player("A", 30) + synthetic_player("B", 7)
        result = audit_cohort(records, holdout_start=date(2025, 2, 10))
        self.assertEqual(result["eligible_player_count"], 1)
        short = next(player for player in result["players"] if player["player_id"] == "B")
        self.assertFalse(short["eligible_for_retrospective_comparison"])
        self.assertEqual(short["stat_diagnostics"], {})
        self.assertIn("INSUFFICIENT_FROZEN_TRAINING_GAMES", short["review_reasons"])

    def test_holdout_after_cutoff_cannot_leak_into_frozen_training_diagnostics(self):
        cutoff = date(2025, 2, 10)
        logs = synthetic_player("A", 25)
        report = audit_cohort(logs, holdout_start=cutoff)
        changed = [
            GameLog(
                game_id=row.game_id, player_id=row.player_id,
                game_date=row.game_date, opponent=row.opponent,
                home=row.home, minutes=row.minutes,
                points=40 if row.game_date >= cutoff else row.points,
                rebounds=30 if row.game_date >= cutoff else row.rebounds,
                assists=15 if row.game_date >= cutoff else row.assists,
            )
            for row in logs
        ]
        comparison = audit_cohort(changed, holdout_start=cutoff)
        self.assertEqual(report["players"][0]["frozen_training_games"],
                         comparison["players"][0]["frozen_training_games"])
        # Changing withheld outcomes should change error scores, not the
        # frozen training policy or training count.
        a = report["players"][0]["stat_diagnostics"]["points"]
        b = comparison["players"][0]["stat_diagnostics"]["points"]
        self.assertNotEqual(a["scores"][0]["mean_absolute_error"],
                            b["scores"][0]["mean_absolute_error"])

    def test_invalid_dates_or_unsupported_sample_size_fail_closed(self):
        logs = synthetic_player("A")
        with self.assertRaises(ValueError):
            audit_cohort(logs, holdout_start=date(2025, 2, 10),
                         holdout_end_exclusive=date(2025, 2, 1))
        with self.assertRaises(ValueError):
            audit_cohort(logs, holdout_start=date(2025, 2, 10),
                         min_training_games=0)
        with self.assertRaises(ValueError):
            audit_cohort([], holdout_start=date(2025, 2, 10))

    def test_manifest_gate_and_original_synthetic_sample(self):
        root = Path(__file__).resolve().parents[1]
        result = audit_local_cohort(
            str(root/"data/demo_games.csv"),
            str(root/"data/demo_games.manifest.json"),
            holdout_start=date(2025, 11, 16),
        )
        self.assertEqual(result["eligible_player_count"], 1)
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["source_rights_independently_verified"])
        self.assertEqual(result["players"][0]["historical_holdout_games"], 5)


if __name__ == "__main__":
    unittest.main()
