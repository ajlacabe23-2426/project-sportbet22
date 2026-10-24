"""Offline integrity and temporal leakage controls."""
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sportprob.governance import DatasetManifest, audit_split, split_by_date, verify_snapshot
from sportprob.ingest import load_game_logs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "demo_games.csv"
MANIFEST = ROOT / "data" / "demo_games.manifest.json"


class DataGovernanceTests(unittest.TestCase):
    def test_manifest_and_snapshot_integrity(self):
        manifest = DatasetManifest.from_file(MANIFEST)
        self.assertTrue(manifest.synthetic)
        self.assertEqual(verify_snapshot(DATA, manifest), sha256(DATA.read_bytes()).hexdigest())

    def test_tampering_is_detected(self):
        manifest = DatasetManifest.from_file(MANIFEST)
        with TemporaryDirectory() as folder:
            file = Path(folder) / "modified.csv"
            file.write_bytes(DATA.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_snapshot(file, manifest)

    def test_rights_restricted_manifest_is_rejected(self):
        original = json.loads(MANIFEST.read_text())
        original["rights_status"] = "pending"
        with TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, "rights_status"):
                DatasetManifest.from_file(path)

    def test_reject_nonresearch_purpose(self):
        original = json.loads(MANIFEST.read_text())
        original["permitted_purpose"] = "commercial"
        with TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, "educational_research"):
                DatasetManifest.from_file(path)

    def test_partition_boundaries(self):
        logs = load_game_logs(DATA)
        train, calibration, holdout = split_by_date(
            logs, train_end_exclusive=date(2025, 11, 11),
            holdout_start_inclusive=date(2025, 11, 16),
        )
        self.assertEqual((len(train), len(calibration), len(holdout)), (10, 5, 5))
        self.assertTrue(all(x.game_date < date(2025, 11, 11) for x in train))
        self.assertTrue(all(date(2025, 11, 11) <= x.game_date < date(2025, 11, 16) for x in calibration))
        self.assertTrue(all(x.game_date >= date(2025, 11, 16) for x in holdout))
        audit = audit_split(
            logs, train_end_exclusive=date(2025, 11, 11),
            holdout_start_inclusive=date(2025, 11, 16),
        )
        self.assertEqual(audit.train_dates, ("2025-11-01", "2025-11-10"))
        self.assertEqual(audit.holdout_dates, ("2025-11-16", "2025-11-20"))

    def test_empty_partition_fails(self):
        with self.assertRaisesRegex(ValueError, "nonempty"):
            audit_split(
                load_game_logs(DATA), train_end_exclusive=date(2025, 11, 11),
                holdout_start_inclusive=date(2025, 12, 1),
            )

    def test_cutoffs_ordered(self):
        with self.assertRaisesRegex(ValueError, "start after"):
            split_by_date(
                load_game_logs(DATA), train_end_exclusive=date(2025, 11, 12),
                holdout_start_inclusive=date(2025, 11, 12),
            )


if __name__ == "__main__":
    unittest.main()
