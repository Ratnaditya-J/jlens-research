#!/usr/bin/env bash
set -euo pipefail
cd /workspace/jlens-research
mkdir -p runs/benchmark-identity runs/lens-numerics runs/speed-benchmark
python -m venv --system-site-packages /workspace/jlens-venv
source /workspace/jlens-venv/bin/activate
python -m pip install 'transformers==4.57.6' 'peft==0.18.1' 'accelerate==1.12.0' 'huggingface_hub==0.36.0' 'safetensors==0.7.0' > runs/benchmark-identity/install.log 2>&1
export IDENTITY_CONFIG=configs/identity-fp32.json
export IDENTITY_OUTPUT=runs/benchmark-identity
timeout --kill-after=60 3600 python -u scripts/gpu_identity.py > runs/benchmark-identity/console.log 2>&1
timeout --kill-after=60 3600 python -u scripts/validate_lens_numerics.py > runs/lens-numerics/console.log 2>&1
timeout --kill-after=60 3600 python -u scripts/speed_benchmark.py > runs/speed-benchmark/console.log 2>&1
touch runs/benchmark-complete
