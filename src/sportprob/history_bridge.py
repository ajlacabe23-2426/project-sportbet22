"""Safely convert a locally held ESPN player-history browser CSV into research format.

This does not download data, clear ESPN rights, or make a future prediction.
Every game/player identifier is checked against the existing export; no IDs,
opponents, playing time or observations are invented.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import re

from .governance import DatasetManifest, verify_snapshot
from .ingest import load_game_logs
from .prepare import normalize_authorized_csv

REQUIRED_BROWSER_FIELDS = {
    "player_name", "game_date", "pts", "reb", "ast", "min",
    "opponent_team", "home_away", "game_id",
}
MAX_INPUT_BYTES = 2_000_000


def convert_browser_history(
    source: str | Path, csv_out: str | Path, manifest_out: str | Path,
    *, expected_espn_id: str, dataset_id: str, source_reference: str,
    rights_evidence: str, confirm_authorized: bool, synthetic: bool = False,
) -> dict:
    """Create an immutable, locally validated snapshot with explicit attestation.

    A user's declaration of authorization does not independently verify rights.
    """
    if not confirm_authorized:
        raise ValueError("explicit source permission confirmation is required")
    if not expected_espn_id.isdecimal() or len(expected_espn_id) > 20:
        raise ValueError("ESPN player ID must contain 1 to 20 digits")
    for label, value in (
        ("dataset_id", dataset_id), ("source_reference", source_reference),
        ("rights_evidence", rights_evidence),
    ):
        if not isinstance(value, str) or not value.strip() or len(value) > 1000:
            raise ValueError(f"{label} is required and limited to 1,000 characters")
    if len(rights_evidence.strip()) < 20:
        raise ValueError("rights_evidence must identify specific permission evidence")
    source, csv_out, manifest_out = map(Path, (source, csv_out, manifest_out))
    if len({path.resolve() for path in (source, csv_out, manifest_out)}) != 3:
        raise ValueError("source and outputs must all be different")
    if csv_out.suffix.lower() != ".csv" or manifest_out.suffix.lower() != ".json":
        raise ValueError("output filenames must end with .csv and .json")
    if csv_out.exists() or manifest_out.exists():
        raise FileExistsError("output already exists; choose new versioned filenames")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("browser CSV exceeds 2 MB limit")

    original_bytes = source.read_bytes()
    original_digest = sha256(original_bytes).hexdigest()
    raw = original_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw, newline=""))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("missing or duplicate source columns")
    if not REQUIRED_BROWSER_FIELDS.issubset(set(reader.fieldnames)):
        raise ValueError("source must be a SportProb historical browser export")
    if len(reader.fieldnames) > 60:
        raise ValueError("excessive source columns")

    canonical_buffer = io.StringIO(newline="")
    headers = [
        "game_id", "player_id", "game_date", "opponent", "home", "minutes",
        "points", "rebounds", "assists",
    ]
    writer = csv.DictWriter(canonical_buffer, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    label_pattern = re.compile(r"^(.+) \(ESPN ([0-9]{1,20})\)$")
    count = 0
    for n, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"row {n}: malformed source record")
        identity = label_pattern.fullmatch(row["player_name"].strip())
        if identity is None or identity.group(2) != expected_espn_id:
            raise ValueError(f"row {n}: ESPN athlete ID mismatch or unsupported label")
        if not identity.group(1).strip():
            raise ValueError(f"row {n}: missing display name")
        # The original source ID is preserved verbatim, namespaced so it can't
        # collide with NBA.com's player ID number.
        writer.writerow({
            "game_id": row["game_id"].strip(),
            "player_id": "ESPN:" + expected_espn_id,
            "game_date": row["game_date"].strip(),
            "opponent": row["opponent_team"].strip(),
            "home": row["home_away"].strip(),
            "minutes": row["min"].strip(),
            "points": row["pts"].strip(),
            "rebounds": row["reb"].strip(),
            "assists": row["ast"].strip(),
        })
        count += 1
    if count == 0:
        raise ValueError("historical browser CSV contains no played games")
    # Reuse the strict canonical parsing and stable game-ID checks rather than
    # weakening the already vetted Python research schema.
    validated, validated_count = normalize_authorized_csv(canonical_buffer.getvalue())
    if validated_count != count:
        raise ValueError("conversion row count mismatch")
    payload = validated.encode("utf-8")
    digest = sha256(payload).hexdigest()
    manifest = {
        "dataset_id": dataset_id.strip(),
        "source_name": "User-supplied SportsDataverse ESPN historical player records",
        "source_reference": source_reference.strip(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": digest,
        "rights_status": "cleared",
        "rights_evidence": rights_evidence.strip(),
        "permitted_purpose": "educational_research",
        "synthetic": synthetic,
    }
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        with csv_out.open("xb") as f:
            created.append(csv_out)
            f.write(payload)
        with manifest_out.open("x", encoding="utf-8") as f:
            created.append(manifest_out)
            json.dump(manifest, f, indent=2)
            f.write("\n")
        verified_manifest = DatasetManifest.from_file(manifest_out)
        verify_snapshot(csv_out, verified_manifest)
        if len(load_game_logs(csv_out)) != count:
            raise ValueError("canonical snapshot did not round-trip")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return {
        "research_only": True,
        "player_id": "ESPN:" + expected_espn_id,
        "rows": count,
        "input_sha256": original_digest,
        "canonical_sha256": digest,
        "data_path": str(csv_out.resolve()),
        "manifest_path": str(manifest_out.resolve()),
        "source_rights_independently_verified": False,
        "real_world_model_accuracy_established": False,
        "synthetic": synthetic,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Offline history-to-research conversion")
    p.add_argument("--source", required=True)
    p.add_argument("--csv-out", required=True)
    p.add_argument("--manifest-out", required=True)
    p.add_argument("--espn-player-id", required=True)
    p.add_argument("--dataset-id", required=True)
    p.add_argument("--source-reference", required=True)
    p.add_argument("--rights-evidence", required=True)
    p.add_argument("--confirm-authorized", action="store_true")
    p.add_argument("--synthetic", action="store_true")
    args = p.parse_args()
    try:
        report = convert_browser_history(
            args.source, args.csv_out, args.manifest_out,
            expected_espn_id=args.espn_player_id,
            dataset_id=args.dataset_id,
            source_reference=args.source_reference,
            rights_evidence=args.rights_evidence,
            confirm_authorized=args.confirm_authorized,
            synthetic=args.synthetic,
        )
    except (OSError, ValueError, UnicodeError) as exc:
        p.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
