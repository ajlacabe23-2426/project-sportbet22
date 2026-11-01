"""Offline research-data normalization and readiness integration tests.

All fixtures are manufactured test observations, never authentic NBA history.
"""
from dataclasses import replace
from datetime import date, timedelta
from hashlib import sha256
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sportprob.governance import DatasetManifest, verify_snapshot
from sportprob.ingest import load_game_logs
from sportprob.prepare import normalize_authorized_csv, prepare_local_dataset
from sportprob.research_check import (
    inspect_research_readiness, audit_authorized_dataset,
)

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "data/demo_games.csv"
DEMO_MANIFEST = ROOT / "data/demo_games.manifest.json"


class LocalResearchPipelineTests(unittest.TestCase):
    def test_prepare_shorthand_source_csv_and_manifest_roundtrip(self):
        source = (
            "GAME_ID,PLAYER_ID,Date,OPP,Home_Away,MIN,PTS,REB,AST,ignored\n"
            "G001,PLAYER-X,2026-01-10,TEAM-A,home,28:30,18,6,4,X\n"
            "G002,PLAYER-X,2026-01-12,TEAM-B,away,31.25,24,8,6,X\n"
        )
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            source_path = folder / "source.csv"
            source_path.write_text(source)
            data_out = folder / "data" / "prepared.csv"
            meta_out = folder / "data" / "prepared.json"
            result = prepare_local_dataset(
                source_path, data_out, meta_out,
                dataset_id="fixture-v1",
                source_name="Unit-test synthetic author",
                source_reference="local-test-suite",
                rights_evidence="Original synthetic rows authored for the unit test",
                confirm_authorized=True, synthetic=True,
            )
            rows = load_game_logs(data_out)
            self.assertEqual(result["rows"], 2)
            self.assertEqual(len(rows), 2)
            self.assertAlmostEqual(rows[0].minutes, 28.5)
            self.assertEqual(rows[0].points, 18)
            self.assertTrue(rows[0].home)
            self.assertFalse(rows[1].home)
            self.assertEqual(rows[1].minutes, 31.25)
            self.assertEqual(verify_snapshot(data_out, DatasetManifest.from_file(meta_out)),
                             sha256(data_out.read_bytes()).hexdigest())
            self.assertTrue(json.loads(meta_out.read_text())["synthetic"])
            self.assertFalse(result["source_rights_independently_verified"])

    def test_prepare_refuses_rights_shortcut_and_existing_outputs(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "source.csv"
            source.write_text(DEMO.read_text())
            path = folder / "normalized.csv"
            meta = folder / "meta.json"
            params = dict(
                dataset_id="demo", source_name="fixture", source_reference="local",
                rights_evidence="Original synthetic fixture written for software tests",
            )
            with self.assertRaisesRegex(ValueError, "explicit confirmation"):
                prepare_local_dataset(source, path, meta, confirm_authorized=False, **params)
            with self.assertRaisesRegex(ValueError, "rights_evidence"):
                prepare_local_dataset(
                    source, path, meta, confirm_authorized=True,
                    **{**params, "rights_evidence": "yes"}
                )
            first = prepare_local_dataset(
                source, path, meta, confirm_authorized=True, synthetic=True, **params
            )
            self.assertEqual(first["rows"], 20)
            prior = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "already exists"):
                prepare_local_dataset(
                    source, path, meta, confirm_authorized=True, synthetic=True, **params
                )
            self.assertEqual(path.read_bytes(), prior)

    def test_normalizer_rejects_invented_and_bad_records(self):
        head = "game_id,player_id,game_date,opponent,home,minutes,points,rebounds,assists\n"
        valid = "001,P,2026-01-05,OPP,true,28,21,7,3\n"
        examples = [
            ("002,P,2026-01-07,OPP,maybe,20,10,2,1\n", "home"),
            ("002,P,2026-01-07,OPP,away,28:77,10,2,1\n", "minutes"),
            ("002,P,2026-01-07,OPP,away,28,-1,2,1\n", "points"),
            ("002,P,2026-01-07,OPP,away,0,10,2,1\n", "positive minutes"),
            ("002,P,2099-01-07,OPP,away,28,10,2,1\n", "future-dated"),
            ("001,P,2026-01-05,OPP,true,28,21,7,3\n", "duplicate"),
            ("002,P,2026-02-31,OPP,true,28,21,7,3\n", "day"),
        ]
        for extra, match in examples:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                normalize_authorized_csv(head + valid + extra)
        with self.assertRaisesRegex(ValueError, "player_id"):
            normalize_authorized_csv(head.replace("player_id", "player_name") + valid)

    def test_quality_gate_synthetic_demonstration_status(self):
        result = audit_authorized_dataset(
            str(DEMO), str(DEMO_MANIFEST), "DEMO-001",
            train_end=date(2025, 11, 11), holdout_start=date(2025, 11, 16),
        )
        self.assertEqual(result["readiness"]["status"], "DEMONSTRATION_ONLY")
        self.assertEqual(result["readiness"]["train_played_games"], 10)
        self.assertEqual(result["readiness"]["calibration_played_games"], 5)
        self.assertEqual(result["readiness"]["holdout_played_games"], 5)
        self.assertIn("SYNTHETIC_NOT_REAL_GAME_EVIDENCE", result["readiness"]["issues"])
        self.assertFalse(result["real_world_forecast_calibration_verified"])

    def test_untampered_structure_can_be_ready_without_claiming_real_accuracy(self):
        template = load_game_logs(DEMO)[0]
        start = date(2026, 1, 1)
        rows = [
            replace(template, game_id=f"EX-{i:03}", player_id="PLAYER-SAMPLE",
                    game_date=start + timedelta(days=i * 2),
                    opponent=f"TEST-OPP-{i % 8}", home=bool(i % 2))
            for i in range(60)
        ]
        report = inspect_research_readiness(
            rows, "PLAYER-SAMPLE", synthetic=False,
            train_end=start + timedelta(days=70),
            holdout_start=start + timedelta(days=90),
        )
        self.assertEqual(report.train_played_games, 35)
        self.assertEqual(report.calibration_played_games, 10)
        self.assertEqual(report.holdout_played_games, 15)
        self.assertEqual(report.issues, ())
        self.assertEqual(
            report.status, "STRUCTURALLY_READY_RIGHTS_AND_ACCURACY_UNVERIFIED"
        )

    def test_bad_history_is_flagged_without_fake_game_synthesis(self):
        logs = load_game_logs(DEMO)
        rows = [
            replace(row, player_id="P", opponent="" if i == 0 else row.opponent,
                    home=None if i == 1 else row.home,
                    game_date=date(2025, 11, 1) if i == 2 else row.game_date)
            for i, row in enumerate(logs)
        ]
        report = inspect_research_readiness(
            rows, "P", synthetic=False,
            train_end=date(2025, 11, 11), holdout_start=date(2025, 11, 16),
        )
        self.assertEqual(report.status, "REVIEW_REQUIRED")
        self.assertEqual(report.missing_opponent_rows, 1)
        self.assertEqual(report.missing_home_flags, 1)
        self.assertIn("MULTIPLE_PLAYER_GAMES_SAME_DAY_REVIEW", report.issues)
        with self.assertRaisesRegex(ValueError, "player was not found"):
            inspect_research_readiness(
                rows, "UNKNOWN", synthetic=False,
                train_end=date(2025, 11, 11), holdout_start=date(2025, 11, 16),
            )


if __name__ == "__main__":
    unittest.main()
