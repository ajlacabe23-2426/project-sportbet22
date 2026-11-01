"""Offline two-season history conversion and date-safe partition tests.

All tests use manufactured fixture values, never ESPN-owned records.
"""
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import json
import subprocess
import sys
import unittest

from sportprob.governance import DatasetManifest, verify_snapshot
from sportprob.history_bridge import convert_browser_history
from sportprob.ingest import load_game_logs
from sportprob.split_plan import plan_historical_partitions

ROOT = Path(__file__).resolve().parents[1]


def sample_browser_csv(rows: int = 90) -> str:
    """Synthesize one player across two calendar years and multiple opponents."""
    header = ("player_name,game_date,pts,reb,ast,min,opponent_team,"
              "home_away,game_id\n")
    start = date(2025, 1, 1)
    out = [header]
    for i in range(rows):
        dt = start + timedelta(days=2 * i)
        out.append(
            f"Example Player (ESPN 3975),{dt.isoformat()},"
            f"{13+i%19},{3+i%7},{2+i%5},{20+i%16},"
            f"ESPN_TEAM_{i%11},{'home' if i%2 else 'away'},G-{i:04}\n"
        )
    return "".join(out)


def create_fixture(folder: Path, raw: str | None = None, *, synthetic: bool = True):
    source = folder / "source.csv"
    data = folder / "prepared.csv"
    manifest = folder / "prepared.manifest.json"
    source.write_text(sample_browser_csv() if raw is None else raw, encoding="utf-8")
    result = convert_browser_history(
        source, data, manifest, expected_espn_id="3975",
        dataset_id="fixture-two-seasons",
        source_reference="local://hand-authored-fixture",
        rights_evidence="Original synthetic fixture written specifically for these tests",
        confirm_authorized=True, synthetic=synthetic,
    )
    return source, data, manifest, result


class HistoryBridgeTests(unittest.TestCase):
    def test_exact_source_ids_and_snapshot_manifest(self):
        with TemporaryDirectory() as folder:
            source, data, manifest, result = create_fixture(Path(folder))
            self.assertEqual(result["rows"], 90)
            self.assertTrue(result["synthetic"])
            self.assertFalse(result["source_rights_independently_verified"])
            self.assertEqual(len(result["input_sha256"]), 64)
            self.assertEqual(len(result["canonical_sha256"]), 64)
            records = load_game_logs(data)
            self.assertEqual(len(records), 90)
            self.assertEqual(records[0].game_id, "G-0000")
            self.assertEqual(records[0].player_id, "ESPN:3975")
            self.assertEqual(records[0].opponent, "ESPN_TEAM_0")
            self.assertFalse(records[0].home)
            self.assertTrue(records[1].home)
            self.assertEqual(
                verify_snapshot(data, DatasetManifest.from_file(manifest)),
                result["canonical_sha256"],
            )
            self.assertNotEqual(result["input_sha256"], result["canonical_sha256"])

    def test_permission_confirmation_and_identity_checks_fail_closed(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "source.csv"
            data = folder / "data.csv"
            manifest = folder / "manifest.json"
            source.write_text(sample_browser_csv())
            kwargs = dict(
                expected_espn_id="3975", dataset_id="test",
                source_reference="local://test",
                rights_evidence="Original synthetic fixture written by this test",
                synthetic=True,
            )
            with self.assertRaisesRegex(ValueError, "permission confirmation"):
                convert_browser_history(
                    source, data, manifest, confirm_authorized=False, **kwargs
                )
            source.write_text(sample_browser_csv().replace(
                "(ESPN 3975)", "(ESPN 201939)"
            ))
            with self.assertRaisesRegex(ValueError, "athlete ID mismatch"):
                convert_browser_history(
                    source, data, manifest, confirm_authorized=True, **kwargs
                )
            self.assertFalse(data.exists())
            self.assertFalse(manifest.exists())

    def test_duplicates_and_bad_minutes_do_not_produce_partial_outputs(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            source, data, manifest, _ = create_fixture(folder)
            before = data.read_bytes()
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                convert_browser_history(
                    source, data, manifest, expected_espn_id="3975",
                    dataset_id="test", source_reference="local://test",
                    rights_evidence="An original synthetic fixture written for software tests",
                    confirm_authorized=True, synthetic=True,
                )
            self.assertEqual(data.read_bytes(), before)
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            raw = sample_browser_csv(2)
            raw = raw.replace("G-0001", "G-0000")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                create_fixture(folder, raw)
            self.assertFalse((folder / "prepared.csv").exists())
            self.assertFalse((folder / "prepared.manifest.json").exists())
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            raw = sample_browser_csv(2).replace(",20,ESPN_TEAM", ",100,ESPN_TEAM")
            with self.assertRaisesRegex(ValueError, "minutes"):
                create_fixture(folder, raw)
            self.assertFalse((folder / "prepared.csv").exists())

    def test_deterministic_no_same_day_split(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            _, data, manifest, _ = create_fixture(folder)
            logs = load_game_logs(data)
            one = plan_historical_partitions(
                logs, player_id="ESPN:3975", synthetic=True
            )
            two = plan_historical_partitions(
                list(reversed(logs)), player_id="ESPN:3975", synthetic=True
            )
            self.assertEqual(one, two)
            self.assertEqual(
                one["train_played_games"]
                + one["calibration_played_games"]
                + one["historical_evaluation_games"], 90,
            )
            self.assertEqual(one["readiness_status"], "DEMONSTRATION_ONLY")
            self.assertFalse(one["genuinely_untouched_forward_validation"])
            self.assertTrue(one["observed_outcomes_previously_visible"])
            train_end = date.fromisoformat(one["training_end_exclusive"])
            holdout_start = date.fromisoformat(one["holdout_start_inclusive"])
            self.assertLess(train_end, holdout_start)
            self.assertTrue(any(r.game_date == train_end for r in logs))
            self.assertTrue(any(r.game_date == holdout_start for r in logs))
            self.assertEqual(len([r for r in logs if r.game_date < train_end]),
                             one["train_played_games"])

    def test_split_same_day_games_stay_together(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            _, data, _, _ = create_fixture(folder)
            original = load_game_logs(data)
            from dataclasses import replace
            second_game = replace(original[35], game_id="GAME-SECOND",
                                  game_date=original[34].game_date)
            records = original + [second_game]
            plan = plan_historical_partitions(
                records, player_id="ESPN:3975", synthetic=True
            )
            self.assertEqual(
                plan["train_played_games"]
                + plan["calibration_played_games"]
                + plan["historical_evaluation_games"], 91,
            )

    def test_cli_plan_retains_checksum_and_no_live_data_claims(self):
        with TemporaryDirectory() as folder:
            _, data, manifest, _ = create_fixture(Path(folder))
            command = [
                sys.executable, "-m", "sportprob.split_plan",
                "--data", str(data), "--manifest", str(manifest),
                "--player", "ESPN:3975",
            ]
            env = dict(__import__("os").environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            run = subprocess.run(command, env=env, cwd=ROOT,
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertEqual(report["dataset_id"], "fixture-two-seasons")
            self.assertFalse(report["real_world_model_accuracy_established"])
            self.assertEqual(len(report["dataset_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
