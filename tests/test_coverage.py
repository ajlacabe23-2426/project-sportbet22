"""Research readiness checks for offline player coverage."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from sportprob.coverage import audit_local_coverage, evaluate_player_coverage
from sportprob.schema import GameLog


class CoverageTests(unittest.TestCase):
    def make_logs(self, count=35):
        start = date(2025, 1, 1)
        return [
            GameLog(
                game_id=f"G-{i}", player_id="DEMO", game_date=start+timedelta(days=i*3),
                opponent=f"OPP-{i%8}", home=bool(i%2), minutes=26.0,
                points=12+i%8, rebounds=4+i%4, assists=2+i%3,
            )
            for i in range(count)
        ]

    def test_structural_readiness_is_not_accuracy_proof(self):
        result = evaluate_player_coverage(self.make_logs(), "DEMO", synthetic=False)
        self.assertEqual(result.status, "STRUCTURALLY_READY_FOR_RESEARCH_UNVERIFIED")
        self.assertEqual(result.played_games, 35)
        self.assertEqual(result.review_reasons, ())

    def test_synthetic_records_never_count_as_real_evidence(self):
        result = evaluate_player_coverage(self.make_logs(), "DEMO", synthetic=True)
        self.assertEqual(result.status, "DEMONSTRATION_ONLY")
        self.assertIn("SYNTHETIC_DATA_NOT_REAL_WORLD_EVIDENCE", result.review_reasons)

    def test_short_sample_requires_review(self):
        result = evaluate_player_coverage(self.make_logs(8), "DEMO", synthetic=False)
        self.assertEqual(result.status, "REVIEW_REQUIRED")
        self.assertIn("INSUFFICIENT_PLAYED_GAMES", result.review_reasons)
        self.assertIn("SHORT_OBSERVATION_WINDOW", result.review_reasons)

    def test_unrecognized_player_does_not_invent_observations(self):
        result = evaluate_player_coverage(self.make_logs(), "MISSING", synthetic=False)
        self.assertEqual(result.played_games, 0)
        self.assertEqual(result.status, "REVIEW_REQUIRED")

    def test_invalid_sample_floor_refused(self):
        with self.assertRaises(ValueError):
            evaluate_player_coverage(self.make_logs(), "DEMO", synthetic=False, minimum_games=0)

    def test_checksum_gated_sample_stays_demonstration_only(self):
        root = Path(__file__).resolve().parents[1]
        audit = audit_local_coverage(
            str(root/"data/demo_games.csv"),
            str(root/"data/demo_games.manifest.json"),
            "DEMO-001",
        )
        self.assertTrue(audit["synthetic"])
        self.assertEqual(audit["player_coverage"]["status"], "DEMONSTRATION_ONLY")
        self.assertFalse(audit["forecast_calibration_verified"])
        self.assertFalse(audit["rights_independently_verified"])


if __name__ == "__main__":
    unittest.main()
