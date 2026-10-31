"""Offline dataset provenance and chronological split audits.

This module does not download data, grant data rights, or connect to wagering
services. It validates a local checksum and a documented research-only policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

from .schema import GameLog


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    source_name: str
    source_reference: str
    retrieved_at: datetime
    sha256: str
    rights_status: str
    rights_evidence: str
    permitted_purpose: str
    synthetic: bool

    @classmethod
    def from_file(cls, path: str | Path) -> "DatasetManifest":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("manifest must be a JSON object")
        required = {
            "dataset_id", "source_name", "source_reference", "retrieved_at",
            "sha256", "rights_status", "rights_evidence", "permitted_purpose",
            "synthetic",
        }
        if set(raw) != required:
            raise ValueError(f"manifest keys mismatch: expected {sorted(required)}")
        for field in required - {"synthetic"}:
            if not isinstance(raw[field], str) or not raw[field].strip():
                raise ValueError(f"{field} must be a nonempty string")
        if type(raw["synthetic"]) is not bool:
            raise ValueError("synthetic must be a boolean")
        if raw["rights_status"] != "cleared":
            raise ValueError("rights_status must be 'cleared' before research use")
        if raw["permitted_purpose"] != "educational_research":
            raise ValueError("only educational_research is supported")
        digest = raw["sha256"].lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("sha256 must be 64 hexadecimal digits")
        try:
            timestamp = datetime.fromisoformat(raw["retrieved_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("retrieved_at must be an ISO 8601 timestamp") from exc
        if timestamp.tzinfo is None:
            raise ValueError("retrieved_at must include a timezone")
        if timestamp.astimezone(timezone.utc) > datetime.now(timezone.utc):
            raise ValueError("retrieved_at cannot be in the future")
        return cls(
            dataset_id=raw["dataset_id"], source_name=raw["source_name"],
            source_reference=raw["source_reference"], retrieved_at=timestamp,
            sha256=digest, rights_status=raw["rights_status"],
            rights_evidence=raw["rights_evidence"],
            permitted_purpose=raw["permitted_purpose"], synthetic=raw["synthetic"],
        )


def verify_snapshot(data_path: str | Path, manifest: DatasetManifest) -> str:
    """Verify local bytes; a matching checksum does not establish legal rights."""
    digest = sha256(Path(data_path).read_bytes()).hexdigest()
    if digest != manifest.sha256:
        raise ValueError("dataset SHA-256 mismatch: immutable snapshot changed")
    return digest


@dataclass(frozen=True, slots=True)
class ChronologicalAudit:
    train_rows: int
    calibration_rows: int
    holdout_rows: int
    train_dates: tuple[str, str] | None
    calibration_dates: tuple[str, str] | None
    holdout_dates: tuple[str, str] | None


def split_by_date(
    logs: Iterable[GameLog], *,
    train_end_exclusive: date,
    holdout_start_inclusive: date,
) -> tuple[list[GameLog], list[GameLog], list[GameLog]]:
    """Partition by calendar date; never split games on the same date."""
    if train_end_exclusive >= holdout_start_inclusive:
        raise ValueError("holdout must start after the training cutoff")
    train: list[GameLog] = []
    calibration: list[GameLog] = []
    holdout: list[GameLog] = []
    for record in logs:
        if record.game_date < train_end_exclusive:
            train.append(record)
        elif record.game_date < holdout_start_inclusive:
            calibration.append(record)
        else:
            holdout.append(record)
    return train, calibration, holdout


def audit_split(
    logs: Iterable[GameLog], *,
    train_end_exclusive: date,
    holdout_start_inclusive: date,
) -> ChronologicalAudit:
    train, calibration, holdout = split_by_date(
        logs,
        train_end_exclusive=train_end_exclusive,
        holdout_start_inclusive=holdout_start_inclusive,
    )
    if not train or not calibration or not holdout:
        raise ValueError("all three chronological partitions must be nonempty")
    keys: set[tuple[str, str]] = set()
    for record in train + calibration + holdout:
        key = (record.player_id, record.game_id)
        if key in keys:
            raise ValueError("duplicate player/game across partitions")
        keys.add(key)
    def bounds(partition: list[GameLog]) -> tuple[str, str]:
        dates = [row.game_date for row in partition]
        return min(dates).isoformat(), max(dates).isoformat()
    return ChronologicalAudit(
        train_rows=len(train), calibration_rows=len(calibration),
        holdout_rows=len(holdout),
        train_dates=bounds(train), calibration_dates=bounds(calibration),
        holdout_dates=bounds(holdout),
    )
