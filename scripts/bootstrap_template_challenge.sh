#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in 0|1|2|3) shard="$1" ;; *) exit 2 ;; esac
cd /workspace/jlens-research
export IDENTITY_CONFIG=configs/identity-fp32.json
export BEHAVIOR_CONFIG=configs/template-challenge-v1.json
export BEHAVIOR_OUTPUT="runs/template-challenge-shard-${shard}"
export EPISODE_SHARD_INDEX="$shard"
export EPISODE_SHARD_COUNT=4
/workspace/jlens-venv/bin/python -u scripts/behavior_pilot.py
/workspace/jlens-venv/bin/python -u scripts/postprocess_fresh.py --shard "$shard" \
  --config configs/template-challenge-v1.json \
  --input-prefix runs/template-challenge-shard \
  --output-prefix runs/template-challenge-processed
