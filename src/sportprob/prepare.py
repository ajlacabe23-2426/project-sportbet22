"""Offline preparation of user-supplied, permissioned player game logs.

No network access, automatic provider downloads, or rights acquisition.
Transforms source-neutral column aliases into SportProb's strict canonical CSV
and emits a declaration-based, SHA-256-bound research manifest.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
from hashlib import sha256
import io
import json
from math import isfinite
from pathlib import Path

from .ingest import load_game_logs

FIELDS = (
    "game_id", "player_id", "game_date", "opponent", "home",
    "minutes", "points", "rebounds", "assists",
)
ALIASES = {
    "game_id": ("game_id", "gameid"),
    "player_id": ("player_id", "playerid"),
    "game_date": ("game_date", "date"),
    "opponent": ("opponent", "opp", "opponent_team"),
    "home": ("home", "home_away", "location"),
    "minutes": ("minutes", "min", "mp"),
    "points": ("points", "pts"),
    "rebounds": ("rebounds", "reb"),
    "assists": ("assists", "ast"),
}
MAX_INPUT_BYTES = 25_000_000
MAX_RECORDS = 100_000


def _minutes(value: str) -> str:
    value = value.strip()
    if ":" in value:
        pieces = value.split(":")
        if len(pieces) != 2 or not all(p.isdigit() for p in pieces):
            raise ValueError("minutes must be decimal or MM:SS")
        m, s = map(int, pieces)
        if s >= 60:
            raise ValueError("minutes seconds must be below 60")
        minutes = m + s / 60
    else:
        try:
            minutes = float(value)
        except ValueError as exc:
            raise ValueError("minutes must be decimal or MM:SS") from exc
    if not isfinite(minutes) or not 0 <= minutes <= 80:
        raise ValueError("minutes must be finite and between 0 and 80")
    return format(minutes, ".6f").rstrip("0").rstrip(".")


def _home(value: str) -> str:
    value = value.strip().lower()
    if value in ("true", "1", "home", "h"):
        return "true"
    if value in ("false", "0", "away", "a"):
        return "false"
    if not value:
        return ""
    raise ValueError("home must be true/false, home/away, 1/0 or blank")


def normalize_authorized_csv(raw: str) -> tuple[str, int]:
    """Normalize common field aliases; never synthesize missing observations."""
    reader = csv.DictReader(io.StringIO(raw.lstrip("\ufeff"), newline=""))
    if not reader.fieldnames:
        raise ValueError("input CSV requires a header")
    headers = [h.strip().lower() for h in reader.fieldnames]
    if len(headers) > 60 or len(set(headers)) != len(headers):
        raise ValueError("duplicate or excessive source columns")
    positions = {}
    for field, aliases in ALIASES.items():
        matches = [i for i, header in enumerate(headers) if header in aliases]
        if len(matches) != 1:
            raise ValueError(f"{field} requires exactly one recognized source column")
        positions[field] = reader.fieldnames[matches[0]]

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    seen: set[tuple[str, str]] = set()
    count = 0
    for number, row in enumerate(reader, start=2):
        if count >= MAX_RECORDS:
            raise ValueError("source file exceeds maximum record count")
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"row {number}: unexpected/missing CSV fields")
        record = {field: row[key].strip() for field, key in positions.items()}
        try:
            record["minutes"] = _minutes(record["minutes"])
            record["home"] = _home(record["home"])
            game_date = date.fromisoformat(record["game_date"])
            if game_date.isoformat() != record["game_date"]:
                raise ValueError("game_date must be YYYY-MM-DD")
            if game_date > date.today():
                raise ValueError("future-dated game is not a completed game")
            for field in ("player_id", "game_id", "opponent"):
                if not record[field] or len(record[field]) > 120:
                    raise ValueError(f"{field} is missing or too long")
            for stat in ("points", "rebounds", "assists"):
                value = record[stat]
                if not value.isdecimal() or int(value) > 200:
                    raise ValueError(f"{stat} must be a nonnegative whole number <= 200")
                record[stat] = str(int(value))
            if record["minutes"] == "0" and any(int(record[s]) for s in ("points", "rebounds", "assists")):
                raise ValueError("nonzero counts require positive minutes")
            key = (record["player_id"], record["game_id"])
            if key in seen:
                raise ValueError("duplicate player/game identifier")
            seen.add(key)
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"row {number}: {exc}") from exc
        writer.writerow(record)
        count += 1
    if count == 0:
        raise ValueError("input has no game observations")
    return buffer.getvalue(), count


def prepare_local_dataset(
    input_path: str | Path,
    data_out: str | Path,
    manifest_out: str | Path,
    *,
    dataset_id: str,
    source_name: str,
    source_reference: str,
    rights_evidence: str,
    confirm_authorized: bool,
    synthetic: bool = False,
) -> dict:
    """Create research artifacts only after explicit source-rights declaration.

    Assertions are provided by the dataset owner; they are NOT independently
    checked by this program and must not override provider restrictions.
    """
    if not confirm_authorized:
        raise ValueError("explicit confirmation of authorized educational use required")
    required = {
        "dataset_id": dataset_id,
        "source_name": source_name,
        "source_reference": source_reference,
        "rights_evidence": rights_evidence,
    }
    for key, value in required.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 1000:
            raise ValueError(f"{key} must be an appropriate nonempty source declaration")
    if len(rights_evidence.strip()) < 20:
        raise ValueError("rights_evidence must describe specific permission evidence")
    input_path, data_out, manifest_out = map(Path, (input_path, data_out, manifest_out))
    if len({p.resolve() for p in (input_path, data_out, manifest_out)}) != 3:
        raise ValueError("input and both outputs must be distinct paths")
    if data_out.suffix.lower() != ".csv" or manifest_out.suffix.lower() != ".json":
        raise ValueError("outputs must be .csv and .json")
    if data_out.exists() or manifest_out.exists():
        raise ValueError("output already exists; use new versioned filenames")
    if input_path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 25 MB local safety limit")
    canonical, count = normalize_authorized_csv(input_path.read_text(encoding="utf-8-sig"))
    payload = canonical.encode("utf-8")
    digest = sha256(payload).hexdigest()
    meta = {
        "dataset_id": dataset_id.strip(),
        "source_name": source_name.strip(),
        "source_reference": source_reference.strip(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": digest,
        "rights_status": "cleared",
        "rights_evidence": rights_evidence.strip(),
        "permitted_purpose": "educational_research",
        "synthetic": synthetic,
    }
    data_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        with data_out.open("xb") as target:
            created.append(data_out)
            target.write(payload)
        with manifest_out.open("x", encoding="utf-8") as target:
            created.append(manifest_out)
            target.write(json.dumps(meta, indent=2) + "\n")
        # Round-trip through existing strict ingestion and manifest validation.
        from .governance import DatasetManifest, verify_snapshot
        manifest = DatasetManifest.from_file(manifest_out)
        verify_snapshot(data_out, manifest)
        if len(load_game_logs(data_out)) != count:
            raise ValueError("normalized row count failed read-back")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return {
        "research_only": True,
        "data_path": str(data_out.resolve()),
        "manifest_path": str(manifest_out.resolve()),
        "rows": count,
        "sha256": digest,
        "synthetic": synthetic,
        "source_rights_independently_verified": False,
        "data_authenticity_independently_verified": False,
        "next_step": "run sportprob.research_check before historical evaluation",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline normalization of a user-supplied, authorized player game-log CSV"
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--data-out", required=True)
    parser.add_argument("--manifest-out", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-reference", required=True)
    parser.add_argument("--rights-evidence", required=True)
    parser.add_argument("--confirm-authorized", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    try:
        output = prepare_local_dataset(
            args.input, args.data_out, args.manifest_out,
            dataset_id=args.dataset_id, source_name=args.source_name,
            source_reference=args.source_reference,
            rights_evidence=args.rights_evidence,
            confirm_authorized=args.confirm_authorized,
            synthetic=args.synthetic,
        )
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
