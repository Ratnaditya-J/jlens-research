# J-lens versus activation probe

This study compares a frozen linear activation probe with independently interpreted Jacobian-lens token views on the same locally confirmed GPT-OSS fine-tune. The primary held-out comparison and two stress-test panels are complete. Earlier-position comparisons and offline action-latency scenarios are also complete. The actual monitor-maintenance control is complete; secondary model controls are still running; see [STATUS.md](STATUS.md) and the [completion audit](reports/completion-audit.md).

## Results available now

The primary paired test set contains 464 confirmed evaluation-interference violations and 259 benign episodes. At their validation-selected thresholds, both methods flag all 464 violations; the probe has 13 false positives and J-view has three. J-view flags include ambiguous evidence: requiring “present” evidence detects 285/464 violations. Context-only reviewers also flag all 464 violations, so the endpoint does not establish that internal readouts are necessary.

The authorization/debugging controls expose a probe specificity failure: 47/47 benign cases flag the probe and 0/47 flag J-view. The same pattern holds in the 26 cases labeled benign before the separately disclosed authorization-label aggregation amendment. These four synthetic control families do not estimate deployment false-positive rates.

- [Combined study findings](reports/study-findings.md)
- [Primary findings and four-way table](reports/primary-findings.md)
- [Stress-test findings and labeling qualification](reports/stress-test-findings.md)
- [Primary case-level CSV](reports/final-comparison/cases.csv)
- [Primary J-space casebook](reports/final-comparison/casebook.html)
- [Template challenge](reports/template-challenge-comparison/summary.json)
- [Specificity controls](reports/specificity-controls-comparison/summary.json)
- [Actual monitor-maintenance findings](reports/monitor-controls-comparison/findings.md)
- [All six four-category tables](reports/coverage-overview.md)
- [Earlier 32-token comparison](reports/final-comparison-offset32/summary.json)
- [Earlier 64-token comparison, with unavailable judgments](reports/final-comparison-offset64/summary.json)
- [Full-token J-space casebook](reports/full-trace-casebook/index.html)
- [Offline action-latency scenarios](reports/action-latency-scenarios.md)
- [Fresh-environment reproduction evidence](reports/frozen-reproduction.json)
- [Timing reconstruction evidence](reports/timing-reproduction.json)

Keep development, primary, template and specificity cohorts separate. Unavailable readouts are not negative results. No universal, strategic-intent, causal-mechanism or human-readability claim is established.

## Reproduce frozen comparisons

The frozen comparison inputs are indexed by SHA256 in `configs/stages/compare-*.json`. The local copy of all 71 distinct declared inputs passed verification; see `reports/local-frozen-input-integrity.json`. The existing 26,901-file primary/stress raw archive separately passed checks in `reports/local-raw-archive-integrity.json`; the new control runs still require final backup checks.

The verified environment used Linux and Python 3.12.3. Other Python/platform combinations require separate verification. Create an isolated Python 3.12 environment and install the exact scientific-package versions used for the successful reconstruction:

```bash
python3.12 -m venv work/reproduction-venv
work/reproduction-venv/bin/python -m pip install -r configs/reproduction-requirements.txt
work/reproduction-venv/bin/python scripts/study.py compare --config configs/stages/compare-primary.json
```

The command above is a dry run that checks identity and input hashes and lists outputs. Add `--execute` to reconstruct the tables from existing scores. Equivalent plans exist for `compare-template-challenge.json` and `compare-specificity-controls.json`. Execution writes the configured report files; completed stages verify their saved output hashes before resuming. It does not generate trajectories, call an API or refit a detector.

For an input-only copied repository and fresh virtual environment, use a new destination outside this repository:

```bash
python3.12 scripts/reproduce_frozen_comparisons.py --destination /absolute/path/to/new-reproduction-directory
```

This harness reconstructs all three panels, checks all nine declared output files against the originals, verifies resume and checks that original inputs and outputs remain unchanged. The recorded run passed with exact hashes. Model generation and J-lens refitting are separate GPU stages, not part of this CPU reconstruction.

## Model and method

The analyzed identity combines `ai-safety-institute/cc-gptoss-20b-sutl-b0.0-s200` adapter revision `9e11602b9e67211887229ed20d0ac79e412ee910` with `unsloth/gpt-oss-20b-BF16` revision `cc89b3e7fd423253264883a80a4fa5abc619649f`, expanded to FP32 execution. It is a third-party fine-tune with OpenAI ancestry. See [provenance](reports/provenance.md) and `configs/identity-fp32.json`; correspondence to an exact author-reported evaluation run remains unresolved, so behavioral claims are local confirmations.

The reference J-lens uses 64 disjoint generic fitting passages, source blocks 7/15/21/22 and pre-normalization target block 23. Finite-difference and readout-stability evidence is saved separately; these sampled checks do not establish all-context validity. The raw probe and supervised J-space diagnostic use training-only preprocessing and grouped tuning. The primary rubric uses two blinded automated reviewers with a context-only arm. Neither token displays nor model-generated reasoning are faithful transcripts of intentions.

The single configuration-taking stage interface is `scripts/study.py`: inspect, confirm, collect, fit-lens, fit-probe, score and compare. Optional interventions remain disabled. [Stage documentation](reports/stage-interface.md) describes manifests, dry runs and scope. Individual stage dependencies and GPU execution are pinned in their recorded manifests and bootstrap scripts.

## Resources and remaining work

The four original H200 collection workers were stopped after verified collection. Three workers currently run the remaining model controls: one base worker and two honest-model workers processing opposite queue orders. The monitor worker is stopped after verified completion. The two native model controls have measured-runtime allowances of four hours and retain identical scientific configurations; the honest helper has a two-hour cap. The helper protocol preserves separate snapshots and uses fixed original-worker priority for duplicate cases. All stop after verified collection. Stopped volumes are explicitly retained where unique provenance has not been ruled out; see `reports/resource-retention.json`. Final control results, their reproducibility and backups, and final report reconciliation remain pending. Resource controls are in `configs/resources.json`; credentials are not included in the scientific artifacts.
