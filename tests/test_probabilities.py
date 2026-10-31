"""Deterministic tests for distribution mathematics and point-in-time isolation."""
import math
from datetime import date
from pathlib import Path
import unittest

from sportprob.ingest import load_game_logs
from sportprob.model import forecast, negative_binomial_pmf
from sportprob.schema import GameLog


DATA = Path(__file__).resolve().parents[1] / "data" / "demo_games.csv"


class ProbabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logs = load_game_logs(DATA)

    def test_normalized_and_nonnegative(self):
        pmf = negative_binomial_pmf(22.0, 8.0)
        self.assertAlmostEqual(sum(pmf), 1.0, places=10)
        self.assertTrue(all(math.isfinite(p) and p >= 0 for p in pmf))

    def test_zero_mean(self):
        self.assertEqual(negative_binomial_pmf(0, 5), (1.0,))

    def test_forecast_intervals_and_buckets(self):
        p = forecast(self.logs, "DEMO-001", "points", date(2025, 11, 21))
        lo80, hi80 = p.central_interval(.8)
        lo90, hi90 = p.central_interval(.9)
        self.assertLessEqual(lo90, lo80)
        self.assertLessEqual(hi80, hi90)
        self.assertGreaterEqual(p.expected_stat, 0)
        self.assertAlmostEqual(sum(b.probability for b in p.buckets()), 1.0, places=9)
        self.assertTrue(0 <= p.modal_bucket().low <= p.modal_bucket().high)

    def test_strict_no_future_leakage(self):
        as_of = date(2025, 11, 15)
        baseline = forecast(self.logs, "DEMO-001", "rebounds", as_of)
        future = GameLog(
            game_id="FUTURE", player_id="DEMO-001", game_date=date(2025, 11, 30),
            opponent="TEST", home=None, minutes=30, points=60, rebounds=30, assists=20,
        )
        altered = forecast(self.logs + [future], "DEMO-001", "rebounds", as_of)
        self.assertEqual(baseline.pmf, altered.pmf)

    def test_small_sample_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "prior played games"):
            forecast(self.logs, "DEMO-001", "points", date(2025, 11, 3))

    def test_reject_unsupported_stat(self):
        with self.assertRaisesRegex(ValueError, "unsupported stat"):
            forecast(self.logs, "DEMO-001", "passing_yards", date(2025, 11, 21))


if __name__ == "__main__":
    unittest.main()
