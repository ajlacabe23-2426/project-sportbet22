"""Frozen holdout protection: no same-day or holdout-label leakage."""
from dataclasses import replace
from datetime import date
from pathlib import Path
import unittest

from sportprob.holdout import evaluate_frozen_holdout, wilson_coverage_interval
from sportprob.ingest import load_game_logs
from sportprob.model import forecast

DATA = Path(__file__).resolve().parents[1] / "data" / "demo_games.csv"


class FrozenHoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logs = load_game_logs(DATA)
        cls.start = date(2025, 11, 16)

    def test_basic_frozen_evaluation(self):
        report = evaluate_frozen_holdout(
            self.logs, "DEMO-001", "points", holdout_start=self.start
        )
        self.assertEqual(report.training_games, 15)
        self.assertEqual(report.evaluated_games, 5)
        self.assertEqual(report.holdout_start, "2025-11-16")
        self.assertEqual(report.training_policy, "frozen_pre_holdout_only")
        self.assertFalse(report.calibrated_on_real_nba_data)
        self.assertTrue(0 <= report.coverage_80 <= 1)
        self.assertTrue(0 <= report.coverage_90 <= 1)

    def test_small_sample_coverage_uncertainty_is_reported(self):
        report = evaluate_frozen_holdout(
            self.logs, "DEMO-001", "points", holdout_start=self.start
        )
        self.assertEqual(report.evaluated_games, 5)
        for observed, bounds in (
            (report.coverage_80, report.coverage_80_wilson_95),
            (report.coverage_90, report.coverage_90_wilson_95),
        ):
            self.assertLess(bounds[0], bounds[1])
            self.assertLessEqual(bounds[0], observed)
            self.assertGreaterEqual(bounds[1], observed)
            self.assertTrue(all(0 <= value <= 1 for value in bounds))

    def test_wilson_bounds_reject_invalid_counts(self):
        self.assertAlmostEqual(wilson_coverage_interval(0, 5)[0], 0)
        self.assertAlmostEqual(wilson_coverage_interval(5, 5)[1], 1)
        self.assertLess(wilson_coverage_interval(5, 5)[0], 0.6)
        for hits, games in ((-1, 5), (6, 5), (0, 0)):
            with self.assertRaisesRegex(ValueError, "coverage"):
                wilson_coverage_interval(hits, games)

    def test_frozen_model_never_sees_heldout_labels(self):
        early = [r for r in self.logs if r.game_date < self.start]
        baseline = forecast(early, "DEMO-001", "points", self.start)
        changed = [
            replace(r, points=75) if r.game_date >= self.start else r
            for r in self.logs
        ]
        changed_prior = [r for r in changed if r.game_date < self.start]
        self.assertEqual(
            baseline.pmf,
            forecast(changed_prior, "DEMO-001", "points", self.start).pmf,
        )
        initial_report = evaluate_frozen_holdout(
            self.logs, "DEMO-001", "points", holdout_start=self.start
        )
        changed_report = evaluate_frozen_holdout(
            changed, "DEMO-001", "points", holdout_start=self.start
        )
        self.assertEqual(initial_report.training_games, changed_report.training_games)
        self.assertNotEqual(
            initial_report.mean_negative_log_likelihood,
            changed_report.mean_negative_log_likelihood,
        )

    def test_same_day_records_not_training(self):
        extra = replace(
            self.logs[0], game_id="ANOTHER-GAME",
            game_date=self.start,
        )
        report = evaluate_frozen_holdout(
            self.logs + [extra], "DEMO-001", "rebounds",
            holdout_start=self.start,
        )
        self.assertEqual(report.training_games, 15)
        self.assertEqual(report.evaluated_games, 6)

    def test_end_date_exclusive_and_validated(self):
        report = evaluate_frozen_holdout(
            self.logs, "DEMO-001", "assists", holdout_start=self.start,
            holdout_end_exclusive=date(2025, 11, 18),
        )
        self.assertEqual(report.evaluated_games, 2)
        self.assertEqual(report.last_evaluated_date, "2025-11-17")
        with self.assertRaisesRegex(ValueError, "must follow"):
            evaluate_frozen_holdout(
                self.logs, "DEMO-001", "assists", holdout_start=self.start,
                holdout_end_exclusive=self.start,
            )

    def test_missing_history_holdout_and_duplicates_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "pre-holdout"):
            evaluate_frozen_holdout(
                self.logs, "DEMO-001", "points", holdout_start=date(2025, 11, 3)
            )
        with self.assertRaisesRegex(ValueError, "no eligible holdout"):
            evaluate_frozen_holdout(
                self.logs, "DEMO-001", "points", holdout_start=date(2025, 12, 1)
            )
        with self.assertRaisesRegex(ValueError, "duplicate player/game"):
            evaluate_frozen_holdout(
                self.logs + [self.logs[0]], "DEMO-001", "points",
                holdout_start=self.start,
            )


if __name__ == "__main__":
    unittest.main()
