#!/usr/bin/env bash
set -euo pipefail
cd /workspace/jlens-research
: "${REPLAY_SHARD:?required}"
mkdir -p "runs/replay-$REPLAY_SHARD" "runs/replay-identity-$REPLAY_SHARD"
python -m venv --system-site-packages /workspace/jlens-venv
source /workspace/jlens-venv/bin/activate
python -m pip install 'transformers==4.57.6' 'peft==0.18.1' 'accelerate==1.12.0' 'huggingface_hub==0.36.0' 'safetensors==0.7.0' > "runs/replay-identity-$REPLAY_SHARD/install.log" 2>&1
export IDENTITY_CONFIG=configs/identity-fp32.json
export IDENTITY_OUTPUT="runs/replay-identity-$REPLAY_SHARD"
timeout --kill-after=60 3600 python -u scripts/gpu_identity.py > "runs/replay-identity-$REPLAY_SHARD/console.log" 2>&1
timeout --kill-after=60 7200 python -u scripts/validate_position_replay.py runs/replay-input runs/development-positions.json "runs/replay-$REPLAY_SHARD" --shard "$REPLAY_SHARD" --shards 2 > "runs/replay-$REPLAY_SHARD/console.log" 2>&1
