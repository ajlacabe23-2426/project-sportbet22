"""End-to-end, offline model-audit export checks for the browser dashboard."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import subprocess
import sys
import unittest

from sportprob.bridge import AUDIT_SCHEMA, save_audit_json


ROOT = Path(__file__).resolve().parents[1]


class DashboardBridgeTests(unittest.TestCase):
    def _cli(self, destination: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "sportprob.cli", "compare",
             "--data", str(ROOT / "data/demo_games.csv"),
             "--manifest", str(ROOT / "data/demo_games.manifest.json"),
             "--player", "DEMO-001", "--stat", "points",
             "--start", "2025-11-16",
             "--output", str(destination), *extra],
            cwd=ROOT, env=env, capture_output=True, text=True, check=False,
        )

    def test_full_comparison_exports_browser_readable_json(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "audit.json"
            result = self._cli(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(path.read_text())
            self.assertEqual(report["schema"], AUDIT_SCHEMA)
            self.assertEqual(report["player_id"], "DEMO-001")
            self.assertEqual(report["stat"], "points")
            self.assertTrue(report["synthetic"])
            self.assertEqual(report["evaluated_games"], 5)
            self.assertEqual(report["training_policy"], "frozen_pre_holdout_only")
            self.assertEqual(report["calibration_status"], "UNVERIFIED_RESEARCH_BASELINES")
            self.assertEqual(len(report["scores"]), 2)
            self.assertEqual(len(report["dataset_sha256"]), 64)
            self.assertEqual(json.loads(result.stdout)["local_json_report"], str(path.resolve()))

    def test_no_silent_overwrite_of_existing_audit(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "audit.json"
            self.assertEqual(self._cli(path).returncode, 0)
            prior = path.read_bytes()
            fail = self._cli(path)
            self.assertNotEqual(fail.returncode, 0)
            self.assertEqual(path.read_bytes(), prior)
            success = self._cli(path, "--overwrite")
            self.assertEqual(success.returncode, 0, success.stderr)

    def test_schema_extension_and_nonfinite_output_guard(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            with self.assertRaisesRegex(ValueError, "schema"):
                save_audit_json({"schema": "unknown"}, folder / "bad.json")
            with self.assertRaisesRegex(ValueError, "json filename"):
                save_audit_json({"schema": AUDIT_SCHEMA}, folder / "audit.html")
            with self.assertRaises(ValueError):
                save_audit_json({"schema": AUDIT_SCHEMA, "bad": float("nan")},
                                folder / "nan.json")
            self.assertFalse((folder / "nan.json").exists())


if __name__ == "__main__":
    unittest.main()
