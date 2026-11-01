"""Local SportsDataverse historical-browser import tests: synthetic ESPN-like rows."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import unittest

from sportprob.sdv_history import find_players_in_source, prepare_historical_browser_csv

HEADER = (
    "game_id,athlete_id,athlete_display_name,team_id,game_date,"
    "minutes,points,rebounds,assists,home_away\n"
)
GOOD = HEADER + (
    "401,23,Example Player,GSW,2026-01-05,32:30,24,7,6,home\n"
    "401,45,Example Opponent,BOS,2026-01-05,30,18,5,7,away\n"
    "402,23,Example Player,GSW,2026-01-08,29.5,19,8,4,away\n"
    "402,45,Example Opponent,LAL,2026-01-08,30,22,5,5,home\n"
    "403,23,Example Player,GSW,2026-01-09,0,0,0,0,home\n"
    "403,45,Example Opponent,MIA,2026-01-09,30,22,5,5,away\n"
)


class HistoricalSourceTests(unittest.TestCase):
    def test_lookup_reuses_espn_id_not_nba_id(self):
        with TemporaryDirectory() as folder:
            source=Path(folder)/"source.csv"
            source.write_text(GOOD)
            matches=find_players_in_source(source,"Example Player")
            self.assertEqual(len(matches),1)
            self.assertEqual(matches[0]["espn_athlete_id"],"23")
            self.assertEqual(matches[0]["rows"],3)

    def test_player_history_display_is_not_probability_engine_feed(self):
        with TemporaryDirectory() as folder:
            folder=Path(folder)
            source=folder/"source.csv"
            output=folder/"output.csv"
            source.write_text(GOOD)
            report=prepare_historical_browser_csv(
                source,output,player_id="23",
                acknowledge_private_research=True,
            )
            self.assertEqual(report["played_rows_exported"],2)
            self.assertEqual(report["zero_minute_records_skipped"],1)
            self.assertEqual(report["opponent_unresolved_rows"],0)
            self.assertFalse(report["forecast_engine_connected"])
            self.assertFalse(report["source_terms_independently_cleared"])
            self.assertEqual(len(report["input_sha256"]),64)
            with output.open(newline="") as f:
                lines=list(csv.DictReader(f))
            self.assertEqual(len(lines),2)
            self.assertEqual(lines[0]["player_name"],"Example Player (ESPN 23)")
            self.assertEqual(lines[0]["opponent_team"],"ESPN_TEAM_BOS")
            self.assertEqual(lines[0]["min"],"32.5")
            self.assertEqual(lines[1]["opponent_team"],"ESPN_TEAM_LAL")
            self.assertEqual(lines[1]["home_away"],"away")

    def test_permission_not_auto_assumed_and_no_overwrite(self):
        with TemporaryDirectory() as folder:
            folder=Path(folder)
            source=folder/"input.csv"
            output=folder/"output.csv"
            source.write_text(GOOD)
            with self.assertRaisesRegex(ValueError,"confirm"):
                prepare_historical_browser_csv(
                    source,output,player_id="23",
                    acknowledge_private_research=False,
                )
            self.assertFalse(output.exists())
            prepare_historical_browser_csv(
                source,output,player_id="23",
                acknowledge_private_research=True,
            )
            before=output.read_bytes()
            with self.assertRaisesRegex(ValueError,"new .csv"):
                prepare_historical_browser_csv(
                    source,output,player_id="23",
                    acknowledge_private_research=True,
                )
            self.assertEqual(before,output.read_bytes())

    def test_missing_opponent_is_not_invented(self):
        text=HEADER + (
            "401,23,Example Player,GSW,2026-01-05,32,24,7,6,\n"
            "402,23,Example Player,GSW,2026-01-08,32,24,7,6,\n"
        )
        with TemporaryDirectory() as folder:
            folder=Path(folder)
            source=folder/"one_team.csv"
            output=folder/"output.csv"
            source.write_text(text)
            result=prepare_historical_browser_csv(
                source,output,player_id="23",
                acknowledge_private_research=True,
            )
            self.assertEqual(result["opponent_unresolved_rows"],2)
            with output.open(newline="") as file:
                rows=list(csv.DictReader(file))
            self.assertTrue(all(not r["opponent_team"] for r in rows))
            self.assertTrue(all(not r["home_away"] for r in rows))

    def test_missing_required_columns_and_duplicate_player_game_fail_closed(self):
        with TemporaryDirectory() as folder:
            folder=Path(folder)
            source=folder/"bad.csv"
            output=folder/"out.csv"
            source.write_text(GOOD.replace("athlete_id","not_athlete_id"))
            with self.assertRaisesRegex(ValueError,"athlete_id"):
                prepare_historical_browser_csv(
                    source,output,player_id="23",acknowledge_private_research=True
                )
            source.write_text(GOOD + "401,23,Example Player,GSW,2026-01-05,32,24,7,6,home\n")
            with self.assertRaisesRegex(ValueError,"duplicate player/game_id"):
                prepare_historical_browser_csv(
                    source,output,player_id="23",acknowledge_private_research=True
                )
            self.assertFalse(output.exists())

    def test_future_date_and_invalid_minutes_rejected(self):
        with TemporaryDirectory() as folder:
            folder=Path(folder)
            source=folder/"bad.csv"
            output=folder/"out.csv"
            source.write_text(GOOD.replace("2026-01-05","2099-01-05"))
            with self.assertRaisesRegex(ValueError,"future-dated"):
                prepare_historical_browser_csv(
                    source,output,player_id="23",acknowledge_private_research=True
                )
            source.write_text(GOOD.replace("32:30","32:67"))
            with self.assertRaisesRegex(ValueError,"seconds"):
                prepare_historical_browser_csv(
                    source,output,player_id="23",acknowledge_private_research=True
                )
            self.assertFalse(output.exists())


if __name__=="__main__":
    unittest.main()
