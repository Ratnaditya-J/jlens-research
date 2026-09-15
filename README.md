# J-lens versus activation probe

This study compares a frozen linear activation probe with independently interpreted Jacobian-lens token views on the same locally confirmed GPT-OSS fine-tune. The primary held-out comparison and two stress-test panels are complete. Earlier-position analysis and final packaging are still in progress; see [STATUS.md](STATUS.md) and the [completion audit](reports/completion-audit.md).

## Results available now

The primary paired test set contains 464 confirmed evaluation-interference violations and 259 benign episodes. At their validation-selected thresholds, both methods flag all 464 violations; the probe has 13 false positives and J-view has three. J-view flags include ambiguous evidence: requiring “present” evidence detects 285/464 violations. Context-only reviewers also flag all 464 violations, so the endpoint does not establish that internal readouts are necessary.

The authorization/debugging controls expose a probe specificity failure: 47/47 benign cases flag the probe and 0/47 flag J-view. The same pattern holds in the 26 cases labeled benign before the separately disclosed authorization-label aggregation amendment. These four synthetic control families do not estimate deployment false-positive rates.

- [Primary findings and four-way table](reports/primary-findings.md)
- [Stress-test findings and labeling qualification](reports/stress-test-findings.md)
- [Primary case-level CSV](reports/final-comparison/cases.csv)
- [Primary J-space casebook](reports/final-comparison/casebook.html)
- [Template challenge](reports/template-challenge-comparison/summary.json)
- [Specificity controls](reports/specificity-controls-comparison/summary.json)
- [Fresh-environment reproduction evidence](reports/frozen-reproduction.json)

Keep development, primary, template and specificity cohorts separate. Unavailable readouts are not negative results. No universal, strategic-intent, causal-mechanism or human-readability claim is established.

## Reproduce frozen comparisons

The frozen comparison inputs are indexed by SHA256 in `configs/stages/compare-*.json`. The local copy of all 71 distinct declared inputs passed verification; see `reports/local-frozen-input-integrity.json`. This does not yet certify every raw trajectory archive.

Create an isolated Python environment and install the exact scientific-package versions used for the successful reconstruction:

```bash
python3 -m venv work/reproduction-venv
work/reproduction-venv/bin/python -m pip install -r configs/reproduction-requirements.txt
work/reproduction-venv/bin/python scripts/study.py compare --config configs/stages/compare-primary.json
```

The command above is a dry run that checks identity and input hashes and lists outputs. Add `--execute` to reconstruct the tables from existing scores. Equivalent plans exist for `compare-template-challenge.json` and `compare-specificity-controls.json`. Execution writes the configured report files; completed stages verify their saved output hashes before resuming. It does not generate trajectories, call an API or refit a detector.

For an input-only copied repository and fresh virtual environment, use a new destination outside this repository:

```bash
python3 scripts/reproduce_frozen_comparisons.py --destination /absolute/path/to/new-reproduction-directory
```

This harness reconstructs all three panels, checks all nine declared output files against the originals, verifies resume and checks that original inputs and outputs remain unchanged. The recorded run passed with exact hashes. Model generation and J-lens refitting are separate GPU stages, not part of this CPU reconstruction.

## Model and method

The analyzed identity combines `ai-safety-institute/cc-gptoss-20b-sutl-b0.0-s200` adapter revision `9e11602b9e67211887229ed20d0ac79e412ee910` with `unsloth/gpt-oss-20b-BF16` revision `cc89b3e7fd423253264883a80a4fa5abc619649f`, expanded to FP32 execution. It is a third-party fine-tune with OpenAI ancestry. See [provenance](reports/provenance.md) and `configs/identity-fp32.json`; correspondence to an exact author-reported evaluation run remains unresolved, so behavioral claims are local confirmations.

The reference J-lens uses 64 disjoint generic fitting passages, source blocks 7/15/21/22 and pre-normalization target block 23. Finite-difference and readout-stability evidence is saved separately; these sampled checks do not establish all-context validity. The raw probe and supervised J-space diagnostic use training-only preprocessing and grouped tuning. The primary rubric uses two blinded automated reviewers with a context-only arm. Neither token displays nor model-generated reasoning are faithful transcripts of intentions.

The single configuration-taking stage interface is `scripts/study.py`: inspect, confirm, collect, fit-lens, fit-probe, score and compare. Optional interventions remain disabled. [Stage documentation](reports/stage-interface.md) describes manifests, dry runs and scope. Individual stage dependencies and GPU execution are pinned in their recorded manifests and bootstrap scripts.

## Resources and remaining work

All four H200 collection workers have been stopped after their artifact stages were verified. CPU scoring remains active. Stopped-volume archival and cleanup, complete raw-data integrity checks, timing/layer diagnostics and final scientific synthesis are still pending. Resource controls are in `configs/resources.json`; credentials are not included in the scientific artifacts.
