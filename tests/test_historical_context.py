"""Historical profile diagnostics use completed observations, never future labels."""
from dataclasses import replace
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import subprocess
import sys
import unittest

from sportprob.historical_context import describe_historical_context
from sportprob.ingest import load_game_logs

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"demo_games.csv"
MANIFEST=ROOT/"data"/"demo_games.manifest.json"


class HistoricalContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logs=load_game_logs(DATA)

    def test_observations_and_split_context_are_explicitly_historical(self):
        result=describe_historical_context(
            self.logs, "DEMO-001", "points", date(2025,11,21)
        )
        self.assertFalse(result.future_prediction)
        self.assertEqual(result.games_used,20)
        self.assertEqual(result.average,22.85)
        self.assertEqual(result.first_game,"2025-11-01")
        self.assertEqual(result.last_game,"2025-11-20")
        self.assertEqual(result.home_games.games,10)
        self.assertEqual(result.away_games.games,10)
        self.assertEqual(result.missing_home_flags,0)
        self.assertTrue(result.sample_standard_deviation>0)
        self.assertTrue(result.observed_10th_percentile<=result.median<=result.observed_90th_percentile)
        self.assertTrue(result.production_per_36_played_minutes>0)
        self.assertTrue(all(g.games>=3 for g in result.opponent_samples.values()))

    def test_cutoff_excludes_same_day_and_all_future_games(self):
        as_of=date(2025,11,16)
        before=describe_historical_context(self.logs,"DEMO-001","rebounds",as_of)
        changed=[
            replace(r, rebounds=75)
            if r.game_date>=as_of else r
            for r in self.logs
        ]
        after=describe_historical_context(changed,"DEMO-001","rebounds",as_of)
        self.assertEqual(before,after)
        self.assertEqual(before.games_used,15)
        self.assertEqual(before.last_game,"2025-11-15")

    def test_short_samples_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"prior played games"):
            describe_historical_context(
                self.logs,"DEMO-001","points",date(2025,11,3)
            )
        with self.assertRaisesRegex(ValueError,"unsupported statistic"):
            describe_historical_context(
                self.logs,"DEMO-001","turnovers",date(2025,11,21)
            )
        with self.assertRaisesRegex(ValueError,"history_games"):
            describe_historical_context(
                self.logs,"DEMO-001","points",date(2025,11,21),
                history_games=3
            )

    def test_missing_home_and_single_opponent_sample_not_misread(self):
        sample=[
            replace(r,home=None,opponent="ONE-OFF" if i==0 else r.opponent)
            for i,r in enumerate(self.logs)
        ]
        report=describe_historical_context(
            sample,"DEMO-001","assists",date(2025,11,21)
        )
        self.assertIsNone(report.home_games)
        self.assertIsNone(report.away_games)
        self.assertEqual(report.missing_home_flags,20)
        self.assertNotIn("ONE-OFF",report.opponent_samples)

    def test_offline_cli_checks_source_manifest_and_marks_synthetic(self):
        env=os.environ.copy()
        env["PYTHONPATH"]=str(ROOT/"src")
        process=subprocess.run(
            [sys.executable,"-m","sportprob.cli","history",
             "--data",str(DATA),"--manifest",str(MANIFEST),
             "--player","DEMO-001","--stat","points",
             "--as-of","2025-11-21","--history-games","20"],
            cwd=ROOT,env=env,capture_output=True,text=True,check=False,
        )
        self.assertEqual(process.returncode,0,process.stderr)
        report=json.loads(process.stdout)
        self.assertEqual(report["schema"],"sportprob-retrospective-context-v1")
        self.assertTrue(report["synthetic"])
        self.assertFalse(report["future_prediction"])
        self.assertFalse(report["real_world_accuracy_verified"])
        self.assertEqual(len(report["dataset_sha256"]),64)


if __name__=="__main__":
    unittest.main()
