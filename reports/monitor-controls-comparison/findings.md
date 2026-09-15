# Authorized monitor-maintenance findings

All 24 generated cases performed the authorized toy-monitor maintenance correctly: execution reached the expected state and method-call log, and each returned a plain string. Both blinded automated reviewers labeled every case benign.

| Category | Benign cases |
|---|---:|
| Probe only | 24 |
| J-lens only | 0 |
| Both | 0 |
| Neither | 0 |

The frozen primary probe therefore has 24/24 false positives; the frozen J-view procedure has 0/24. This is a second concrete specificity failure for the probe, alongside the separate authorized-fixture controls. It does not establish a deployment-wide rate: these are four authored maintenance families with six seeds each. The degenerate family-bootstrap intervals cannot prove population-perfect performance for either method. Sensitivity is unmeasured in this entirely benign panel.

The original checkpoint, 64-passage J-lens, code-onset observation boundary and validation-selected thresholds were retained. The 21 downloaded model/tokenizer/adapter files match the original identity audit. All 96 J/context interpretation calls completed without errors through the documented OpenRouter/OpenAI route. Monitor state is observed inside a toy WASI environment, not production infrastructure or tamper-proof attestation.

A fresh Python environment reproduced all three result files exactly in 8.65 seconds. See `../monitor-reproduction.json`; individual cases and scores are in `cases.csv` and `cases.json`. This comparison did not retrain or recalibrate either detector.
