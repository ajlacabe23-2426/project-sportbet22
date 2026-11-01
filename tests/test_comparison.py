"""Tests for proper scoring and leakage-free model comparison."""
from dataclasses import replace
from datetime import date
from math import isfinite
from pathlib import Path
import unittest
from unittest.mock import patch

from sportprob.compare import (
    compare_frozen_distributions, poisson_pmf, ranked_probability_score,
)
from sportprob.ingest import load_game_logs
from sportprob.model import forecast


DATA = Path(__file__).resolve().parents[1] / "data" / "demo_games.csv"


class FrozenDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logs = load_game_logs(DATA)
        cls.cutoff = date(2025, 11, 16)

    def test_poisson_normalization_across_small_and_large_means(self):
        self.assertEqual(poisson_pmf(0), (1.0,))
        for mu in (0.1, 5, 22, 200, 700, 2000):
            pmf = poisson_pmf(mu)
            self.assertAlmostEqual(sum(pmf), 1, places=9)
            self.assertTrue(all(isfinite(p) and 0 <= p <= 1 for p in pmf))
            self.assertAlmostEqual(sum(k * p for k, p in enumerate(pmf)), mu, places=6)

    def test_poisson_invalid_parameters_fail_closed(self):
        for value in (-1.0, float("inf"), float("nan"), 2001):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Poisson"):
                poisson_pmf(value)

    def test_ranked_probability_score_basics(self):
        self.assertAlmostEqual(ranked_probability_score((0.0, 1.0), 1), 0)
        self.assertAlmostEqual(ranked_probability_score((1.0,), 1), 1)
        self.assertAlmostEqual(ranked_probability_score((0.5, 0.5), 0), 0.25)
        for pmf, actual in [((0.6, 0.6), 1), ((float("nan"),), 0), ((1.0,), -1)]:
            with self.assertRaises(ValueError):
                ranked_probability_score(pmf, actual)

    def test_comparison_returns_two_distinct_distributions_with_common_mean(self):
        result = compare_frozen_distributions(
            self.logs, "DEMO-001", "points", holdout_start=self.cutoff
        )
        self.assertEqual(result.training_games, 15)
        self.assertEqual(result.evaluated_games, 5)
        self.assertEqual(result.training_policy, "frozen_pre_holdout_only")
        self.assertEqual(result.calibration_status, "UNVERIFIED_RESEARCH_BASELINES")
        nb, poisson = result.scores
        self.assertEqual(nb.model, "negative_binomial_provisional")
        self.assertEqual(poisson.model, "poisson_same_mean_benchmark")
        for score in result.scores:
            self.assertEqual(score.evaluated_games, 5)
            self.assertGreaterEqual(score.mean_negative_log_likelihood, 0)
            self.assertGreaterEqual(score.mean_ranked_probability_score, 0)
            self.assertTrue(0 <= score.coverage_80 <= 1)
            self.assertTrue(0 <= score.coverage_90 <= 1)
            self.assertLessEqual(score.coverage_80_wilson_95[0], score.coverage_80)
            self.assertGreaterEqual(score.coverage_80_wilson_95[1], score.coverage_80)
            self.assertGreaterEqual(score.mean_interval_width_80, 0)
        self.assertAlmostEqual(nb.mean_absolute_error, poisson.mean_absolute_error)
        self.assertAlmostEqual(
            nb.mean_bias_observed_minus_expected,
            poisson.mean_bias_observed_minus_expected,
        )
        self.assertNotAlmostEqual(
            nb.mean_ranked_probability_score,
            poisson.mean_ranked_probability_score,
        )

    def test_no_holdout_or_same_day_rows_used_as_training(self):
        with patch("sportprob.compare.forecast", wraps=forecast) as called:
            compare_frozen_distributions(
                self.logs, "DEMO-001", "assists", holdout_start=self.cutoff
            )
            self.assertEqual(called.call_count, 5)
            for call in called.call_args_list:
                training = call.args[0]
                self.assertTrue(training)
                self.assertTrue(all(r.game_date < self.cutoff for r in training))
                self.assertTrue(all(r.game_date < call.args[3] for r in training))

        changed = [
            replace(r, rebounds=60) if r.game_date >= self.cutoff else r
            for r in self.logs
        ]
        first = compare_frozen_distributions(
            self.logs, "DEMO-001", "rebounds", holdout_start=self.cutoff
        )
        second = compare_frozen_distributions(
            changed, "DEMO-001", "rebounds", holdout_start=self.cutoff
        )
        self.assertEqual(first.training_games, second.training_games)
        self.assertNotEqual(
            first.scores[0].mean_negative_log_likelihood,
            second.scores[0].mean_negative_log_likelihood,
        )

    def test_cutoff_and_duplicate_games_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "pre-holdout"):
            compare_frozen_distributions(
                self.logs, "DEMO-001", "points", holdout_start=date(2025, 11, 3)
            )
        with self.assertRaisesRegex(ValueError, "no eligible holdout"):
            compare_frozen_distributions(
                self.logs, "DEMO-001", "points", holdout_start=date(2025, 12, 1)
            )
        with self.assertRaisesRegex(ValueError, "duplicate player/game"):
            compare_frozen_distributions(
                self.logs + [self.logs[0]],
                "DEMO-001", "points", holdout_start=self.cutoff
            )
        with self.assertRaisesRegex(ValueError, "must follow"):
            compare_frozen_distributions(
                self.logs, "DEMO-001", "points", holdout_start=self.cutoff,
                holdout_end_exclusive=self.cutoff,
            )
        result = compare_frozen_distributions(
            self.logs, "DEMO-001", "points", holdout_start=self.cutoff,
            holdout_end_exclusive=date(2025, 11, 18),
        )
        self.assertEqual(result.evaluated_games, 2)


if __name__ == "__main__":
    unittest.main()
