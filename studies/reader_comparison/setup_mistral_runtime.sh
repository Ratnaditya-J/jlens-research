#!/usr/bin/env bash
# Reproduce the isolated Linux/Python3.12 runtime; never overwrite an environment.
set -euo pipefail
runtime_dir=${1:?Usage: bash setup_mistral_runtime.sh ABSOLUTE_NEW_VENV [python3.12]}
python_bin=${2:-python3.12}
case "$runtime_dir" in /*) ;; *) echo 'An absolute venv path is required' >&2; exit 2;; esac
if [[ -e "$runtime_dir" ]]; then
  echo 'Refusing to overwrite an existing runtime' >&2
  exit 2
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
uv venv --python "$python_bin" "$runtime_dir"
uv pip sync --python "$runtime_dir/bin/python" "$script_dir/mistral-runtime-requirements.txt"
cuda_root="$runtime_dir/lib/python3.12/site-packages/nvidia/cu13"
test -x "$cuda_root/bin/nvcc"
test -f "$cuda_root/lib/libcudart.so.13"
if [[ ! -e "$cuda_root/lib64" ]]; then ln -s lib "$cuda_root/lib64"; fi
if [[ ! -e "$cuda_root/lib/libcudart.so" ]]; then
  ln -s libcudart.so.13 "$cuda_root/lib/libcudart.so"
fi
{
  printf 'export CUDA_HOME=%q\n' "$cuda_root"
  printf 'export PATH=%q:%q:"$PATH"\n' "$runtime_dir/bin" "$cuda_root/bin"
  printf 'export NVIDIA_TF32_OVERRIDE=0\n'
  printf 'export VLLM_NO_USAGE_STATS=1\nexport DO_NOT_TRACK=1\n'
} > "$runtime_dir/runtime.env"
uv pip check --python "$runtime_dir/bin/python"
source "$runtime_dir/runtime.env"
"$runtime_dir/bin/python" - <<'PY'
from importlib.metadata import version
import torch
for name, expected in {'vllm':'0.30.0', 'transformers':'5.10.4',
                       'nvidia-cuda-nvcc':'13.0.88', 'nvidia-cuda-crt':'13.0.88',
                       'nvidia-nvvm':'13.0.88'}.items():
    assert version(name) == expected, (name, version(name), expected)
assert torch.cuda.is_available(), 'CUDA device required'
from flashinfer.rope import get_rope_module
get_rope_module()
print('Runtime and RoPE build ready. Run the numerical preflight and reader gates separately.')
PY
