#!/usr/bin/env bash
set -euo pipefail
cd /workspace/jlens-research
: "${FIT_SHARD:?FIT_SHARD required}"
mkdir -p "runs/fit64-$FIT_SHARD" "runs/fit64-identity-$FIT_SHARD"
python -m venv --system-site-packages /workspace/jlens-venv
source /workspace/jlens-venv/bin/activate
python -m pip install 'transformers==4.57.6' 'peft==0.18.1' 'accelerate==1.12.0' 'huggingface_hub==0.36.0' 'safetensors==0.7.0' > "runs/fit64-identity-$FIT_SHARD/install.log" 2>&1
export IDENTITY_CONFIG=configs/identity-fp32.json
export IDENTITY_OUTPUT="runs/fit64-identity-$FIT_SHARD"
timeout --kill-after=60 3600 python -u scripts/gpu_identity.py > "runs/fit64-identity-$FIT_SHARD/console.log" 2>&1
timeout --kill-after=60 7200 python -u scripts/fit_pilot_shard.py --shard "$FIT_SHARD" --dim-batch 2 --stage-config /workspace/jlens-research/configs/fit64.json > "runs/fit64-$FIT_SHARD/console.log" 2>&1
