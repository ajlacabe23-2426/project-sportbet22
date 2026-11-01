# Local two-season historical evaluation

SportProb can convert a locally held player-history CSV into the strict
research schema used by its existing quality gates. This is a **local-only,
retrospective** workflow. It does not download, redistribute or publish ESPN
data, and it does not create future-game picks, odds or proposed-line probabilities.

The user's combined browser CSV is expected at
data/processed/curry-history-combined.csv and contains:
player_name,game_date,pts,reb,ast,min,opponent_team,home_away,game_id.

The adapter verifies that the ESPN player label matches the supplied ESPN ID
and preserves source game IDs, dates and opponent context. It creates a
namespaced canonical player ID: ESPN:3975, which is **not** the NBA.com ID.

## 1. Authorize the source, then convert

The project does not independently establish that ESPN permits the intended
reuse. The downstream CC BY repository declaration does not itself clear
upstream rights. Only run this step after reviewing the original provider's
terms and confirming your particular educational use is allowed. Supply
genuine specific permission evidence, not an invented statement.

    cd ~/Desktop/project-sportbet22
    git status --short
    git pull --ff-only origin main
    read -r "RIGHTS_EVIDENCE?Source-specific authorization evidence: "
    PYTHONPATH=src python3.12 -m sportprob.history_bridge \
      --source data/processed/curry-history-combined.csv \
      --csv-out data/processed/curry-research-v1.csv \
      --manifest-out data/processed/curry-research-v1.manifest.json \
      --espn-player-id 3975 \
      --dataset-id curry-2025-2026-research-v1 \
      --source-reference https://github.com/sportsdataverse/hoopR-nba-data \
      --rights-evidence "$RIGHTS_EVIDENCE" \
      --confirm-authorized

Outputs are local, versioned and never silently overwritten. The manifest
records your explicit permission declaration; a successful checksum check
does not make source rights or authenticity independently verified.
If you don't have sufficient permission evidence, **do not run this command**
and do not assert the records are licensed for model evaluation.

## 2. Plan chronological retrospective partitions

    PYTHONPATH=src python3.12 -m sportprob.split_plan \
      --data data/processed/curry-research-v1.csv \
      --manifest data/processed/curry-research-v1.manifest.json \
      --player ESPN:3975

The fixed split targets are 65% training, 15% calibration and 20% historical
evaluation, kept strictly separate by whole calendar dates. The command
prints its cutoffs, partition counts and structural quality warnings.

Because the combined 126 games have already been viewed, this is **not a
genuinely blind or prospective evaluation**. It demonstrates a reproducible
retrospective analysis. Do not present resulting scores as independent
evidence of future predictive accuracy.

## 3. Verify quality counts and sample coverage

Replace the dates below with the exact dates output by the split planner:

    PYTHONPATH=src python3.12 -m sportprob.research_check \
      --data data/processed/curry-research-v1.csv \
      --manifest data/processed/curry-research-v1.manifest.json \
      --player ESPN:3975 \
      --train-end YYYY-MM-DD \
      --holdout-start YYYY-MM-DD

This checks data integrity, game counts, missing context, date separation
and opponent diversity. For appropriately permitted retrospective model
diagnostics, the preexisting sportprob.cli compare command accepts the
same canonical dataset and manifest with the printed holdout-start date.

Model variance assumptions remain provisional. Calendar cutoffs do not
reconstruct when data was originally published or revised. Real-world
calibration remains unverified without independent time-appropriate
out-of-sample observations.
