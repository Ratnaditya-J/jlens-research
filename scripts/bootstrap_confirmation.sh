#!/usr/bin/env bash
set -euo pipefail
cd /workspace/jlens-research
mkdir -p runs/identity-fp32 runs/confirmation
python -m venv --system-site-packages /workspace/jlens-venv
source /workspace/jlens-venv/bin/activate
python -m pip install 'transformers==4.57.6' 'peft==0.18.1' 'accelerate==1.12.0' 'huggingface_hub==0.36.0' 'safetensors==0.7.0' > runs/identity-fp32/install.log 2>&1
export IDENTITY_CONFIG=configs/identity-fp32.json
export IDENTITY_OUTPUT=runs/identity-fp32
timeout --kill-after=60 3600 python -u scripts/gpu_identity.py > runs/identity-fp32/console.log 2>&1
export BEHAVIOR_CONFIG=configs/behavior-confirmation.json
export BEHAVIOR_OUTPUT=runs/confirmation
timeout --kill-after=60 14400 python -u scripts/behavior_pilot.py > runs/confirmation/console.log 2>&1
