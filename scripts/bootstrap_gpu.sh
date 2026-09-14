#!/usr/bin/env bash
set -euo pipefail
cd /workspace/jlens-research
mkdir -p runs/identity
python -m venv --system-site-packages /workspace/jlens-venv
source /workspace/jlens-venv/bin/activate
python -m pip install 'transformers==4.57.6' 'peft==0.18.1' 'accelerate==1.12.0' 'huggingface_hub==0.36.0' 'safetensors==0.7.0' > runs/identity/install.log 2>&1
timeout --signal=TERM --kill-after=60 18000 python -u scripts/gpu_identity.py > runs/identity/console.log 2>&1
