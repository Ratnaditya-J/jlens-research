#!/usr/bin/env bash
set -euo pipefail
cd /workspace/jlens-research
python -m venv --system-site-packages /workspace/jlens-venv
source /workspace/jlens-venv/bin/activate
python -m pip install 'transformers==4.57.6' 'peft==0.18.1' 'accelerate==1.12.0' 'huggingface_hub==0.36.0' 'safetensors==0.7.0' > runs/monitor-install.log 2>&1
python -u scripts/prepare_monitor_model.py > runs/monitor-download.log 2>&1
export IDENTITY_CONFIG=configs/identity-fp32.json BEHAVIOR_CONFIG=configs/monitor-controls-v1.json EPISODE_SHARD_COUNT=4
for shard in 0 1 2 3; do
 export EPISODE_SHARD_INDEX="$shard" BEHAVIOR_OUTPUT="runs/monitor-controls-shard-$shard"
 timeout --kill-after=60 6000 python -u scripts/behavior_pilot.py > "runs/monitor-generation-$shard.log" 2>&1
 python -u scripts/postprocess_fresh.py --shard "$shard" --config configs/monitor-controls-v1.json --input-prefix runs/monitor-controls-shard --output-prefix runs/monitor-controls-processed > "runs/monitor-postprocess-$shard.log" 2>&1
done
