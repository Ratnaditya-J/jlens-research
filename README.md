# J-lens and probe comparison

This repository implements a staged comparison of checkpoint-specific Jacobian-lens readouts and a supervised linear activation probe on independently verified behavior. See [STATUS.md](STATUS.md) for current execution state and [reports/provenance.md](reports/provenance.md) for model identity evidence and unresolved links.

The experiment is in stage zero. No comparison results exist yet. The persistent Codex task advances implementation and experiments every 30 minutes. GPU execution occurs on a tracked RunPod pod; credentials remain in the local control environment.

## Current runnable commands

```bash
python3 scripts/runpod_control.py status
python3 scripts/runpod_control.py stop
python3 scripts/runpod_control.py terminate
```

The remote identity pilot runs `bash scripts/bootstrap_gpu.sh` from `/workspace/jlens-research`. It records downloads, package versions, LoRA differences, no-op hook parity, cached/replay logit differences, finite gradients, a finite-difference sweep, memory and elapsed time. The bootstrap has a five-hour execution timeout; the local controller stops the pod at its six-hour provisioning deadline. Stopped volume storage still incurs charges until terminated. Collect results before termination.

The full inspect → confirm → collect → fit-lens / fit-probe → score → compare interface is still to be implemented. Do not mistake the identity pilot for a completed research pipeline.

## Scientific decisions

- Use the exact pinned BF16 base, adapter and tokenizer; no model fine-tuning is authorized by this project.
- Verify actual violations externally, retaining failed, uncertain and benign attempts.
- Fit the reference J-lens using disjoint generic data. Never relabel a logit lens or tuned lens as J-lens.
- Collect shared trajectories with independent readout branches; freeze all analysis choices before test access.
- Use blinded automated reviewers with executable evidence to avoid dependence on unavailable human reviewers. Report that deviation; do not claim to have measured human readability.
- Compare sensitivity at comparable specificity, held-out transfer, timing, missingness and paired disagreements. Restrict conclusions to the checkpoint, behavior and validated protocol studied.

The user authorizes autonomous execution and replenishing accounts. Resource caps in `configs/resources.json` bound jobs and scaling; balances are not budget estimates. The overall envelope is an agent-selected planning limit drawn from the brief, not a measured forecast or a commitment to spend it.
