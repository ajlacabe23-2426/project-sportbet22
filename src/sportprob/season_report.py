"""Produce a single private, offline report of observed basketball game history.

This is descriptive quality assurance, not a future-game prediction or an
independent statement of rights to ESPN-derived game records. No network calls,
no betting lines, no externally submitted player data.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date
from hashlib import sha256
from html import escape
import json
from math import isfinite
from pathlib import Path
from statistics import mean, median, stdev

BROWSER_FIELDS = {
    "player_name", "game_date", "pts", "reb", "ast", "min",
    "opponent_team", "home_away", "game_id",
}
METRICS = ("points", "rebounds", "assists", "minutes")
STAT_COL = {"points": "pts", "rebounds": "reb", "assists": "ast", "minutes": "min"}
MAX_BYTES = 2_000_000
RAW_LIMIT = 85_000_000


def _rows(path: Path, max_bytes: int) -> tuple[list[dict[str, str]], str]:
    if path.stat().st_size > max_bytes:
        raise ValueError(f"file exceeds local size limit: {path.name}")
    raw_bytes = path.read_bytes()
    decoded = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(decoded.splitlines(keepends=True))
    if (not reader.fieldnames or None in reader.fieldnames
            or len(reader.fieldnames) != len(set(reader.fieldnames))):
        raise ValueError(f"{path.name}: invalid or duplicate CSV columns")
    if len(reader.fieldnames) > 140:
        raise ValueError("excessive CSV columns")
    output = []
    for n, row in enumerate(reader, start=2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"{path.name}: malformed CSV at row {n}")
        output.append(row)
        if len(output) > 200_000:
            raise ValueError("CSV exceeds row safety limit")
    return output, sha256(raw_bytes).hexdigest()


def _valid_date(value: str) -> date:
    d = date.fromisoformat(value)
    if d.isoformat() != value or d > date.today():
        raise ValueError("invalid or future completed-game date")
    return d


def _stat_row(row: dict[str, str]) -> dict[str, float | int]:
    values: dict[str, float | int] = {}
    for metric in METRICS:
        value = (row.get(STAT_COL[metric]) or "").strip()
        if metric == "minutes":
            x = float(value)
            if not isfinite(x) or x <= 0 or x > 80:
                raise ValueError("minutes must be finite, positive and <= 80")
            values[metric] = x
        else:
            if not value.isdecimal() or int(value) > 200:
                raise ValueError(f"{metric} must be a nonnegative whole number <= 200")
            values[metric] = int(value)
    return values


def _describe(records: list[dict], metric: str) -> dict | None:
    if not records:
        return None
    values = [row["values"][metric] for row in records]
    result = {
        "games": len(records),
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
        "standard_deviation": round(stdev(values), 2) if len(values) > 1 else None,
        "observed_min": min(values),
        "observed_max": max(values),
    }
    if metric != "minutes":
        minutes = sum(row["values"]["minutes"] for row in records)
        result["observed_per_36_minutes"] = round(36 * sum(values) / minutes, 2)
    return result


def _stats(records: list[dict]) -> dict:
    return {metric: _describe(records, metric) for metric in METRICS}


def _source_integrity(records: list[dict], *, athlete_id: str,
                      archive_paths: list[Path]) -> dict:
    """Compare selected local rows to raw ESPN athlete/season-type identifiers.

    The supplied raw files are inspected locally. Nothing is uploaded or
    republished. Exact metadata is never inferred from a date range.
    """
    matched: dict[str, dict] = {}
    source_counts = Counter()
    source_dnp = Counter()
    sha_by_file = {}
    for path in archive_paths:
        archive, digest = _rows(path, RAW_LIMIT)
        sha_by_file[path.name] = digest
        for row in archive:
            if row.get("athlete_id") != athlete_id:
                continue
            game = (row.get("game_id") or "").strip()
            if not game or game in matched:
                raise ValueError("raw source has duplicate/missing athlete game ID")
            typecode = (row.get("season_type") or "unknown").strip()
            season = (row.get("season") or path.stem.split("_")[-1]).strip()
            # Filename ending-year labels are an explicit fallback if season
            # is absent; never infer a season from game calendar year alone.
            key = f"{season} | type {typecode}"
            source_counts[key] += 1
            if row.get("did_not_play", "").strip().lower() == "true":
                source_dnp[key] += 1
            matched[game] = {
                "season_label": season,
                "season_type": typecode,
                "date": row.get("game_date", ""),
                "points": row.get("points", ""),
                "rebounds": row.get("rebounds", ""),
                "assists": row.get("assists", ""),
            }
    requested = {r["game_id"] for r in records}
    unmatched = requested - set(matched)
    if unmatched:
        raise ValueError(f"{len(unmatched)} selected game IDs were not found in raw archives")
    season_membership: dict[str, str] = {}
    for row in records:
        raw = matched[row["game_id"]]
        if raw["season_type"] != "2":
            raise ValueError("selected games include non-regular-season source records")
        if row["date"].isoformat() != raw["date"]:
            raise ValueError("selected game date disagrees with source archive")
        for stat in ("points", "rebounds", "assists"):
            value = (raw[stat] or "").strip()
            if not value.isdecimal() or int(value) != row["values"][stat]:
                raise ValueError(f"selected {stat} disagrees with source archive")
        season_membership[row["game_id"]] = raw["season_label"]
    return {
        "archive_sha256": sha_by_file,
        "source_rows_by_season_and_type": dict(sorted(source_counts.items())),
        "did_not_play_rows_by_season_and_type": dict(sorted(source_dnp.items())),
        "selected_rows_matched_to_archive": len(season_membership),
        "selected_nonregular_rows": 0,
        "season_by_game": season_membership,
    }


def make_report(
    data_path: str | Path, *,
    player_id: str, train_end: date, evaluation_start: date,
    raw_sources: list[str | Path] | None = None,
) -> dict:
    """Analyze a strictly local regular-season sample without fitting a model."""
    if not player_id.isdecimal() or len(player_id) > 20:
        raise ValueError("ESPN athlete ID must contain 1 to 20 digits")
    if not isinstance(train_end, date) or not isinstance(evaluation_start, date):
        raise ValueError("cutoffs must be valid dates")
    if not train_end < evaluation_start:
        raise ValueError("training cutoff must precede evaluation start")
    path = Path(data_path)
    csv_rows, digest = _rows(path, MAX_BYTES)
    if not csv_rows:
        raise ValueError("no historical games found")
    if not BROWSER_FIELDS.issubset(csv_rows[0]):
        raise ValueError("CSV is missing expected SportProb historical columns")
    records: list[dict] = []
    game_ids = set()
    for n, row in enumerate(csv_rows, start=2):
        label = row["player_name"].strip()
        if not label.endswith(f"(ESPN {player_id})"):
            raise ValueError(f"row {n}: ESPN player identity differs")
        game_id = row["game_id"].strip()
        if not game_id or game_id in game_ids:
            raise ValueError(f"row {n}: missing or duplicate game ID")
        game_ids.add(game_id)
        when = _valid_date(row["game_date"].strip())
        home = row["home_away"].strip().lower()
        if home not in ("home", "away", ""):
            raise ValueError(f"row {n}: unknown home/away value")
        try:
            values = _stat_row(row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"row {n}: {exc}") from exc
        records.append({
            "game_id": game_id, "date": when,
            "home": home, "opponent": row["opponent_team"].strip(),
            "values": values,
        })
    records.sort(key=lambda r: (r["date"], r["game_id"]))
    selected_sources = [Path(p) for p in (raw_sources or [])]
    source_audit = _source_integrity(
        records, athlete_id=player_id, archive_paths=selected_sources
    ) if selected_sources else None
    by_phase = {
        "training": [r for r in records if r["date"] < train_end],
        "calibration": [r for r in records if train_end <= r["date"] < evaluation_start],
        "historical_evaluation": [r for r in records if r["date"] >= evaluation_start],
    }
    if any(not part for part in by_phase.values()):
        raise ValueError("all three chronological periods must have played games")
    seasons = {}
    if source_audit:
        membership = source_audit.pop("season_by_game")
        labels = sorted(set(membership.values()))
        seasons = {
            label: _stats([r for r in records if membership[r["game_id"]] == label])
            for label in labels
        }
    season_changes = {}
    if len(seasons) >= 2:
        labels = list(seasons)
        for earlier, later in zip(labels, labels[1:]):
            season_changes[f"{earlier} to {later}"] = {
                metric: round(
                    seasons[later][metric]["mean"] - seasons[earlier][metric]["mean"], 2
                )
                for metric in METRICS
            }
    venues = {
        "home": _stats([r for r in records if r["home"] == "home"]),
        "away": _stats([r for r in records if r["home"] == "away"]),
        "unknown": sum(not r["home"] for r in records),
    }
    return {
        "schema": "sportprob-offline-historical-observations-v1",
        "research_only": True,
        "future_prediction": False,
        "model_evaluation_performed": False,
        "genuinely_blind_validation": False,
        "player_id": f"ESPN:{player_id}",
        "dataset_file": path.name,
        "dataset_sha256": digest,
        "source_rights_independently_verified": False,
        "source_authenticity_independently_verified": False,
        "scope": "locally supplied regular-season played games",
        "selected_games": len(records),
        "first_game": records[0]["date"].isoformat(),
        "last_game": records[-1]["date"].isoformat(),
        "source_verified_season_type_2": source_audit is not None,
        "cutoffs": {
            "training_end_exclusive": train_end.isoformat(),
            "historical_evaluation_start_inclusive": evaluation_start.isoformat(),
        },
        "overall": _stats(records),
        "periods": {name: _stats(part) for name, part in by_phase.items()},
        "seasons": seasons,
        "season_to_season_mean_changes": season_changes,
        "venue": venues,
        "source_audit": source_audit,
        "last_five_completed_games": _stats(records[-5:]),
        "notes": [
            "All measures describe previously completed games; not forecasts or target-line probabilities.",
            "The source file is user supplied. A matching checksum does not establish data rights.",
            "Already viewed outcomes do not constitute an untouched prospective test.",
            "Season type 2 and season grouping are verified only when raw archives are supplied.",
            "Missing or excluded participation records must not be interpreted as zero-point games.",
            "Venue differences and seasonal patterns are associations, not causal matchup effects.",
        ],
    }


def _fmt(value: int | float | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _table(name: str, stats: dict) -> str:
    rows = []
    for metric, data in stats.items():
        if data is None:
            continue
        rows.append(
            "<tr><th scope='row'>" + escape(metric.title()) + "</th>"
            + "".join(f"<td>{_fmt(data[key])}</td>"
                      for key in ("mean", "median", "standard_deviation",
                                  "observed_min", "observed_max"))
            + f"<td>{_fmt(data.get('observed_per_36_minutes'))}</td>"
            + "</tr>"
        )
    return (
        f"<section><h2>{escape(name)}</h2><div class='scroll'><table>"
        "<thead><tr><th>Metric</th><th>Mean</th><th>Median</th>"
        "<th>SD</th><th>Min</th><th>Max</th><th>Per 36 min</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div></section>"
    )


def render_html(report: dict) -> str:
    sections = [_table(f"All {report['selected_games']} completed games", report["overall"])]
    for name, content in report["periods"].items():
        games = content["points"]["games"]
        sections.append(_table(f"{name.replace('_', ' ').title()} · {games} games", content))
    for name, content in report["seasons"].items():
        sections.append(_table(f"Source season {name} · {content['points']['games']} games", content))
    if report["season_to_season_mean_changes"]:
        for title, changes in report["season_to_season_mean_changes"].items():
            season_rows = "".join(
                f"<tr><th scope='row'>{escape(metric.title())}</th>"
                f"<td>{changes[metric]:+.2f}</td></tr>"
                for metric in METRICS
            )
            sections.append(
                f"<section><h2>Season mean change · {escape(title)}</h2>"
                "<p>Later minus earlier season; observed descriptive change.</p>"
                "<div class='scroll'><table><thead><tr><th>Metric</th>"
                "<th>Change in mean</th></tr></thead><tbody>"
                + season_rows + "</tbody></table></div></section>"
            )
    for name in ("home", "away"):
        if report["venue"][name]["points"]:
            sections.append(_table(name.title() + " completed games", report["venue"][name]))
    sections.append(_table("Last five completed games", report["last_five_completed_games"]))
    provenance = (
        "<p>Dataset file: <code>" + escape(report["dataset_file"]) +
        "</code> · SHA-256: <code>" + escape(report["dataset_sha256"]) + "</code></p>"
    )
    if report["source_audit"]:
        source_audit = report["source_audit"]
        provenance += "<p>Selected games matched against local raw archive: " + str(
            source_audit["selected_rows_matched_to_archive"]
        ) + ". Season-type 2 only.</p>"
        provenance += "<h3>Original source record counts</h3><ul>"
        for key, value in source_audit["source_rows_by_season_and_type"].items():
            dnp = source_audit["did_not_play_rows_by_season_and_type"].get(key, 0)
            provenance += f"<li>{escape(key)}: {value} source records, {dnp} marked did not play</li>"
        provenance += "</ul>"
    notes = "".join(f"<li>{escape(note)}</li>" for note in report["notes"])
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; "
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
        "<title>SportProb historical research summary</title>"
        "<style>:root{color-scheme:dark;font-family:system-ui,Arial,sans-serif}"
        "body{background:#09141e;color:#eaf1f5;line-height:1.55;margin:0}"
        "main{max-width:980px;margin:auto;padding:30px 18px 70px}"
        "h1{font-size:clamp(1.8rem,4vw,2.7rem);line-height:1.15}"
        "h2{font-size:1.2rem;margin:0 0 14px}"
        "p,li{color:#becbd3}header{border-bottom:1px solid #344b59;padding-bottom:15px}"
        ".tag{color:#d4ef7d;letter-spacing:.11em;font-size:.75rem;font-weight:bold}"
        "section{border:1px solid #304350;border-radius:14px;background:#10222f;"
        "padding:18px;margin-top:15px}.scroll{overflow:auto}"
        "table{border-collapse:collapse;width:100%;text-align:right;white-space:nowrap}"
        "th,td{border-bottom:1px solid #344756;padding:9px}"
        "th:first-child{text-align:left}code{overflow-wrap:anywhere}"
        "</style></head><body><main><header>"
        "<div class='tag'>SPORTPROB / LOCAL HISTORICAL RESEARCH</div>"
        "<h1>Completed game performance report</h1>"
        "<p>ESPN athlete " + escape(report["player_id"].split(":")[-1])
        + " · " + escape(report["first_game"]) + " through "
        + escape(report["last_game"]) + " · " + str(report["selected_games"])
        + " selected played games</p>"
        "<p>Observed past records only. Not a prediction or independently "
        "licensed dataset.</p></header>"
        + "".join(sections) + "<section><h2>Source and research limitations</h2>"
        + provenance + "<ul>" + notes + "</ul></section>"
        "</main></body></html>"
    )


def save_reports(report: dict, output_html: str | Path, output_json: str | Path) -> dict:
    paths = [Path(output_html), Path(output_json)]
    if paths[0].resolve() == paths[1].resolve():
        raise ValueError("HTML and JSON output paths must be distinct")
    if paths[0].suffix.lower() != ".html" or paths[1].suffix.lower() != ".json":
        raise ValueError("outputs must end in .html and .json")
    if any(path.exists() for path in paths):
        raise FileExistsError("report output already exists; choose a versioned name")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        with paths[0].open("x", encoding="utf-8") as f:
            created.append(paths[0])
            f.write(render_html(report))
        with paths[1].open("x", encoding="utf-8") as f:
            created.append(paths[1])
            f.write(json.dumps(report, indent=2) + "\n")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return {
        "html": str(paths[0].resolve()),
        "json": str(paths[1].resolve()),
        "selected_games": report["selected_games"],
        "source_archive_crosscheck": report["source_verified_season_type_2"],
        "future_prediction": False,
    }


def suggest_chronological_cutoffs(data_path: str | Path) -> tuple[date, date]:
    """Allocate ~65/15/20 by complete calendar days without using stat outcomes."""
    rows, _ = _rows(Path(data_path), MAX_BYTES)
    if len(rows) < 50:
        raise ValueError("at least 50 completed games are needed for automatic partitions")
    counts = Counter(_valid_date(row["game_date"].strip()) for row in rows)
    days = sorted(counts)
    if len(days) < 3:
        raise ValueError("at least three calendar dates are required")
    targets = (len(rows) * .65, len(rows) * .80)
    positions = []
    cumulative = 0
    for index, day in enumerate(days[:-1]):
        cumulative += counts[day]
        if len(positions) < 2 and cumulative >= targets[len(positions)]:
            positions.append(days[index + 1])
    if len(positions) != 2 or positions[0] >= positions[1]:
        raise ValueError("cannot form three non-overlapping historical date partitions")
    before = sum(n for day, n in counts.items() if day < positions[0])
    middle = sum(n for day, n in counts.items() if positions[0] <= day < positions[1])
    after = len(rows) - before - middle
    if before < 30 or middle < 10 or after < 10:
        raise ValueError("automatic partitions lack 30/10/10 completed games")
    return positions[0], positions[1]


def main() -> None:
    p = argparse.ArgumentParser(
        description="Local retrospective historical game report; no forecasting"
    )
    p.add_argument("--data", required=True)
    p.add_argument("--espn-player-id", required=True)
    p.add_argument("--train-end", help="exclusive YYYY-MM-DD training cutoff")
    p.add_argument("--evaluation-start", help="inclusive YYYY-MM-DD historical evaluation cutoff")
    p.add_argument("--auto-splits", action="store_true", help="fixed 65/15/20 date-safe retrospective partition")
    p.add_argument("--raw", nargs="*", default=[], help="original local season CSV files")
    p.add_argument("--html-out", help="new local .html output")
    p.add_argument("--json-out", help="new local .json output")
    p.add_argument("--output-stem", help="write HTML and JSON using a versioned filename stem")
    args = p.parse_args()
    try:
        if args.auto_splits:
            if args.train_end or args.evaluation_start:
                raise ValueError("--auto-splits must not be mixed with explicit cutoffs")
            train_end, eval_start = suggest_chronological_cutoffs(args.data)
            policy = "fixed_65_15_20_by_calendar_date_retrospective"
        else:
            if not args.train_end or not args.evaluation_start:
                raise ValueError("provide both explicit cutoffs or --auto-splits")
            train_end = date.fromisoformat(args.train_end)
            eval_start = date.fromisoformat(args.evaluation_start)
            policy = "user_supplied_retrospective_cutoffs"
        if args.output_stem:
            if args.html_out or args.json_out:
                raise ValueError("--output-stem must not be mixed with individual output paths")
            output_html = args.output_stem + ".html"
            output_json = args.output_stem + ".json"
        else:
            if not args.html_out or not args.json_out:
                raise ValueError("provide both --html-out and --json-out or --output-stem")
            output_html, output_json = args.html_out, args.json_out
        report = make_report(
            args.data, player_id=args.espn_player_id,
            train_end=train_end, evaluation_start=eval_start,
            raw_sources=args.raw,
        )
        report["split_policy"] = policy
        result = save_reports(report, output_html, output_json)
        result["split_policy"] = policy
        result["training_end_exclusive"] = train_end.isoformat()
        result["evaluation_start"] = eval_start.isoformat()
    except (OSError, ValueError, UnicodeError) as exc:
        p.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
