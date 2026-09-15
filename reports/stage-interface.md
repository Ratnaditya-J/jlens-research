# Reproducing stages

Run from the research repository. The interface defaults to a dry-run:

```sh
python scripts/study.py fit-lens --config configs/stages/fit64-0.json
```

The plan validates input and script SHA256 values, pinned base/adapter revisions, expected output paths, and stage membership. It prints estimated GPU memory/hours and commands. It does not load a model or spend API credits. Add `--execute` only in the pinned runtime on the appropriate allocated worker:

```sh
python scripts/study.py fit-lens --config configs/stages/fit64-0.json --execute
```

Do not run this alongside the active controller-managed GPU workload. The CLI does not provision resources, enforce the cloud scheduler's concurrency limit, or replace the independent deadline watchdog. Use the recorded worker runtime and `/workspace/jacobian-lens` reference source. Its `python` must be the pinned GPU venv for GPU stages or CPU scientific venv for calibration/evaluation. External behavioral execution remains WASI-only.

Each executed plan writes `runs/stage-manifests/STAGE/PLAN_SHA256/` containing its plan, status, console output and completion hashes. A repeated completed plan verifies outputs and returns without rerunning. Changed inputs or completed outputs are rejected. Failed stages retain logs; underlying generation/fitting/review stages retain their own restartable checkpoints. A successful process is not automatically a passed scientific gate: inspect the stage's scientific report.

| Interface stage | Implemented script choices |
|---|---|
| inspect | gpu_identity.py |
| confirm | review_batch.py |
| collect | behavior_pilot.py |
| fit-lens | fit_pilot_shard.py, merge_fit_shards.py, validate_readouts64.py |
| fit-probe | calibrate_fresh.py, supervised_jspace.py |
| score | assemble_fresh.py, postprocess_fresh.py, interpret_fresh.py |
| compare | evaluate_fresh.py, supervised_jspace.py, build_casebook.py, paired_breakdown.py |
| intervene | Explicitly disabled; optional causal intervention work has not been performed |

A stage configuration contains `stage`, `identity_config`, `inputs_sha256`, `commands` (script, argument list, optional environment), `outputs`, `resource_estimate`, and `scope`. All input/output paths are repository-relative. Every invoked script and the identity configuration require hashes. Include the relevant scientific input artifacts and imported implementation files, not just the top-level script. Script calls use an argument list, never shell evaluation. Do not put credentials in configuration files; supply them through the existing private runtime mechanism.

Ready configuration examples include FP32 identity inspection, four fresh generation shards and four 64-passage fitting shards under `configs/stages/`. Configurations for downstream frozen results must be generated after those inputs exist; unset or missing hashes are rejected. Complete downstream reproduction commands and the final artifact manifest remain pending collection of the real outputs.

Verification: `python tests/test_stage_cli.py` exercises a synthetic temporary repository. It checks that dry-run creates no result, verified resume executes only once, changed outputs are rejected, and changed source hashes invalidate the plan. Synthetic tests are not observations about the studied checkpoint.
