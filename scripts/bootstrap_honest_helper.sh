#!/usr/bin/env bash
set -euo pipefail
cd /workspace/jlens-research
: "${CONTROL_ROLE:?}"
mkdir -p "runs/secondary-$CONTROL_ROLE"
python -m venv --system-site-packages /workspace/jlens-venv
source /workspace/jlens-venv/bin/activate
python -m pip install 'transformers==4.57.6' 'accelerate==1.12.0' 'huggingface_hub==0.36.0' 'safetensors==0.7.0' > "runs/secondary-$CONTROL_ROLE/install.log" 2>&1
python -u scripts/prepare_model_control.py > "runs/secondary-$CONTROL_ROLE/download.log" 2>&1
export IDENTITY_CONFIG="configs/secondary-$CONTROL_ROLE-identity.json"
export BEHAVIOR_CONFIG="configs/secondary-$CONTROL_ROLE-v1.json"
export BEHAVIOR_OUTPUT="runs/secondary-$CONTROL_ROLE"
timeout --kill-after=60 6600 python -u scripts/behavior_model_controls_reverse.py > "runs/secondary-$CONTROL_ROLE/console.log" 2>&1
