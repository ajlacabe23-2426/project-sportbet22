"""Offline visual report regression tests."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sportprob.governance import DatasetManifest, verify_snapshot
from sportprob.ingest import load_game_logs
from sportprob.model import forecast
from sportprob.report import render_forecast_report, save_forecast_report

ROOT = Path(__file__).resolve().parents[1]


class HtmlReportTests(unittest.TestCase):
    def test_escapes_source_content_and_has_no_external_execution(self):
        manifest = DatasetManifest.from_file(ROOT / "data/demo_games.manifest.json")
        digest = verify_snapshot(ROOT / "data/demo_games.csv", manifest)
        pred = forecast(load_game_logs(ROOT / "data/demo_games.csv"),
                        "DEMO-001", "points", date(2025, 11, 21))
        html = render_forecast_report(
            pred, dataset_id=manifest.dataset_id, dataset_sha256=digest,
            source_name='</p><script>alert("x")</script>', synthetic=True)
        self.assertIn("ENGINEERED SYNTHETIC DATA", html)
        self.assertIn("Full count-distribution buckets", html)
        self.assertIn("80% central model interval", html)
        self.assertIn("SHA-256 verified", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("default-src 'none'", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_report_is_writable_only_with_explicit_replace(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "reports" / "demo.html"
            saved = save_forecast_report("<h1>demo</h1>", path)
            self.assertEqual(saved, path.resolve())
            self.assertEqual(path.read_text(), "<h1>demo</h1>")
            with self.assertRaises(FileExistsError):
                save_forecast_report("changed", path)
            self.assertEqual(path.read_text(), "<h1>demo</h1>")
            save_forecast_report("changed", path, overwrite=True)
            self.assertEqual(path.read_text(), "changed")


if __name__ == "__main__":
    unittest.main()
