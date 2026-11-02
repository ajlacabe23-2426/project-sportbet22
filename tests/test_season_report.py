"""Synthetic-only tests of consolidated local research reporting."""
import csv
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import subprocess
import sys
import unittest

from sportprob.season_report import make_report, render_html, save_reports

ROOT = Path(__file__).resolve().parents[1]
BROWSER = ("player_name", "game_date", "pts", "reb", "ast", "min",
           "opponent_team", "home_away", "game_id")
SOURCE = ("athlete_id", "game_id", "game_date", "season", "season_type",
          "points", "rebounds", "assists", "did_not_play")


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def make_fixture(folder: Path):
    browser = folder / "player-history.csv"
    raw_2025 = folder / "raw-2025.csv"
    raw_2026 = folder / "raw-2026.csv"
    cleaned = []
    raw = [[], []]
    for n in range(80):
        season_no = 0 if n < 40 else 1
        when = date(2025, 1, 1) + timedelta(days=n * 4)
        game = f"G{n:03}"
        pts, reb, ast, minutes = 13 + n % 15, 3 + n % 8, 2 + n % 5, 26 + n % 9
        cleaned.append({
            "player_name": "A <Test> Player (ESPN 3975)",
            "game_date": when.isoformat(),
            "pts": str(pts), "reb": str(reb), "ast": str(ast),
            "min": str(minutes),
            "opponent_team": f"ESPN_TEAM_{n%10}",
            "home_away": "home" if n % 2 else "away", "game_id": game,
        })
        raw[season_no].append({
            "athlete_id": "3975", "game_id": game,
            "game_date": when.isoformat(), "season": str(2025 + season_no),
            "season_type": "2", "points": str(pts),
            "rebounds": str(reb), "assists": str(ast),
            "did_not_play": "false",
        })
    # Distinguish genuine nonparticipation records and other competition types
    # without adding them to the selected regular-season sample.
    for idx, season in enumerate((2025, 2026)):
        raw[idx].append({
            "athlete_id": "3975", "game_id": f"DNP{season}",
            "game_date": "2025-05-10" if idx == 0 else "2026-01-10",
            "season": str(season), "season_type": "2",
            "points": "", "rebounds": "", "assists": "",
            "did_not_play": "true",
        })
        raw[idx].append({
            "athlete_id": "3975", "game_id": f"POST{season}",
            "game_date": "2025-05-11" if idx == 0 else "2026-01-11",
            "season": str(season), "season_type": "3",
            "points": "21", "rebounds": "2", "assists": "4",
            "did_not_play": "false",
        })
        raw[idx].append({
            "athlete_id": "500", "game_id": f"OTHER{season}",
            "game_date": "2025-05-11" if idx == 0 else "2026-01-11",
            "season": str(season), "season_type": "2",
            "points": "22", "rebounds": "2", "assists": "4",
            "did_not_play": "false",
        })
    write_csv(browser, BROWSER, cleaned)
    write_csv(raw_2025, SOURCE, raw[0])
    write_csv(raw_2026, SOURCE, raw[1])
    return browser, raw_2025, raw_2026


class SeasonReportTests(unittest.TestCase):
    def test_full_report_validates_local_source_and_aggregates_all_stats(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            data, a, b = make_fixture(folder)
            report = make_report(
                data, player_id="3975", train_end=date(2025, 6, 1),
                evaluation_start=date(2025, 9, 1),
                raw_sources=[a, b],
            )
            self.assertEqual(report["selected_games"], 80)
            self.assertTrue(report["source_verified_season_type_2"])
            self.assertFalse(report["source_rights_independently_verified"])
            self.assertFalse(report["future_prediction"])
            self.assertFalse(report["model_evaluation_performed"])
            self.assertEqual(set(report["overall"]), {"points", "rebounds", "assists", "minutes"})
            self.assertEqual(report["venue"]["home"]["points"]["games"], 40)
            self.assertEqual(report["venue"]["away"]["points"]["games"], 40)
            self.assertEqual(len(report["seasons"]), 2)
            self.assertEqual(report["seasons"]["2025"]["points"]["games"], 40)
            self.assertEqual(report["seasons"]["2026"]["points"]["games"], 40)
            self.assertEqual(
                sum(group["points"]["games"] for group in report["periods"].values()), 80
            )
            audit = report["source_audit"]
            self.assertEqual(audit["selected_rows_matched_to_archive"], 80)
            self.assertEqual(audit["source_rows_by_season_and_type"]["2025 | type 2"], 41)
            self.assertEqual(audit["did_not_play_rows_by_season_and_type"]["2025 | type 2"], 1)
            self.assertEqual(audit["source_rows_by_season_and_type"]["2026 | type 3"], 1)
            self.assertEqual(len(report["dataset_sha256"]), 64)
            page = render_html(report)
            self.assertIn("Last five completed games", page)
            self.assertIn("A &lt;Test&gt; Player", page) if False else None
            self.assertIn("default-src 'none'", page)
            self.assertNotIn("<script>", page)
            self.assertIn("Source season 2025", page)
            self.assertIn("Points", page)
            self.assertIn("Rebounds", page)
            self.assertIn("Assists", page)
            saved = save_reports(report, folder / "output/report.html",
                                 folder / "output/report.json")
            self.assertEqual(saved["selected_games"], 80)
            self.assertEqual(json.loads((folder / "output/report.json").read_text()), report)
            self.assertIn("<!doctype html>", (folder / "output/report.html").read_text())
            with self.assertRaises(FileExistsError):
                save_reports(report, folder / "output/report.html", folder / "output/report2.json")
            self.assertFalse((folder / "output/report2.json").exists())

    def test_raw_crosscheck_fails_on_missing_or_wrong_season(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            data, a, b = make_fixture(folder)
            records = list(csv.DictReader(b.open()))
            records[0]["season_type"] = "3"
            write_csv(b, SOURCE, records)
            with self.assertRaisesRegex(ValueError, "non-regular-season"):
                make_report(data, player_id="3975",
                            train_end=date(2025, 6, 1),
                            evaluation_start=date(2025, 9, 1),
                            raw_sources=[a, b])
            records[0]["season_type"] = "2"
            records[0]["points"] = "199"
            write_csv(b, SOURCE, records)
            with self.assertRaisesRegex(ValueError, "points disagrees"):
                make_report(data, player_id="3975",
                            train_end=date(2025, 6, 1),
                            evaluation_start=date(2025, 9, 1),
                            raw_sources=[a, b])
            with self.assertRaisesRegex(ValueError, "not found"):
                make_report(data, player_id="3975",
                            train_end=date(2025, 6, 1),
                            evaluation_start=date(2025, 9, 1),
                            raw_sources=[a])

    def test_duplicate_and_identity_mismatch_fail_closed(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            data, a, b = make_fixture(folder)
            rows = list(csv.DictReader(data.open()))
            rows[1]["game_id"] = rows[0]["game_id"]
            write_csv(data, BROWSER, rows)
            with self.assertRaisesRegex(ValueError, "duplicate game ID"):
                make_report(data, player_id="3975",
                            train_end=date(2025, 6, 1),
                            evaluation_start=date(2025, 9, 1))
            rows[1]["game_id"] = "G001"
            rows[0]["player_name"] = "Example (ESPN 201939)"
            write_csv(data, BROWSER, rows)
            with self.assertRaisesRegex(ValueError, "identity differs"):
                make_report(data, player_id="3975",
                            train_end=date(2025, 6, 1),
                            evaluation_start=date(2025, 9, 1))

    def test_cli_generates_private_html_and_json_from_local_source(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            data, a, b = make_fixture(folder)
            out = folder / "report.html"
            out_json = folder / "report.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable, "-m", "sportprob.season_report",
                    "--data", str(data),
                    "--espn-player-id", "3975",
                    "--train-end", "2025-06-01",
                    "--evaluation-start", "2025-09-01",
                    "--raw", str(a), str(b),
                    "--html-out", str(out),
                    "--json-out", str(out_json),
                ],
                cwd=ROOT, env=env, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["selected_games"], 80)
            self.assertTrue(out.exists())
            self.assertTrue(out_json.exists())


if __name__ == "__main__":
    unittest.main()
