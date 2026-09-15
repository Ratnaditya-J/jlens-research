# J-lens versus activation probe: study findings

**Status:** Scientific results assembled; final completion audit and remaining control-scope/resource checks are in progress.

## Answer

Neither method is a complete misalignment detector. In this experiment, the separately calibrated activation probe detects substantially more confirmed violations 32 tokens before code onset, while the J-view detects some violations the probe misses. The probe fails the authorized-control specificity test, and its code-onset calibration fails when applied unchanged at earlier positions. J-view results depend strongly on whether ambiguous evidence counts as a flag and on the context shown to reviewers.

The evidence supports a checkpoint-, dataset-, position- and interpretation-specific comparison. It does not support universal superiority of either method, faithful access to intentions, or deployment readiness.

## The four categories

Each table includes only known-label cases with paired readouts at that endpoint. “Violation” means independently adjudicated, externally evidenced evaluation interference. A flag is a thresholded detector result, not ground truth. The same episodes recur across timing endpoints, so these rows must not be added together.

### Primary: immediately before submitted code

| Category | Confirmed violation | Benign | Total |
|---|---:|---:|---:|
| Probe only | 0 | 12 | 12 |
| J-view only | 0 | 2 | 2 |
| Both flag | 464 | 1 | 465 |
| Neither flags | 0 | 244 | 244 |

Paired cases: **723**. Probe sensitivity **100.0%**, false-positive rate **5.0%**; J-view sensitivity **100.0%**, false-positive rate **1.2%**.

### Secondary: 32 tokens before code onset

| Category | Confirmed violation | Benign | Total |
|---|---:|---:|---:|
| Probe only | 115 | 15 | 130 |
| J-view only | 21 | 22 | 43 |
| Both flag | 302 | 2 | 304 |
| Neither flags | 7 | 135 | 142 |

Paired cases: **619**. Probe sensitivity **93.7%**, false-positive rate **9.8%**; J-view sensitivity **72.6%**, false-positive rate **13.8%**.

### Secondary: 64 tokens before code onset

| Category | Confirmed violation | Benign | Total |
|---|---:|---:|---:|
| Probe only | 14 | 5 | 19 |
| J-view only | 10 | 0 | 10 |
| Both flag | 7 | 0 | 7 |
| Neither flags | 37 | 46 | 83 |

Paired cases: **119**. Probe sensitivity **30.9%**, false-positive rate **9.8%**; J-view sensitivity **25.0%**, false-positive rate **0.0%**.

The primary and the two secondary endpoints have separately trained/calibrated probes and validation-selected thresholds. They also have different available-case populations. Their rates are not a longitudinal curve for one unchanged detector.

At −32, the paired sensitivity advantage of the probe is 21.1 percentage points, with a 95% family-cluster bootstrap interval of 14.1–27.7 points. At −64, the interval for the difference spans −11.9 to +25.6 points, so the small sample does not establish a clear sensitivity difference. Empirical zero-error bootstrap intervals can collapse; they do not prove zero population error.

## What the main result does—and does not—show

The primary J threshold flags scores 1 (ambiguous) and 2 (present). Of 464 positive cases, 179 are ambiguous and 285 are present. Requiring present evidence alone gives 61.4% sensitivity and no observed benign flags. That is a descriptive ordinal operating point, not a replacement of the frozen primary threshold.

Context-only reviewers also detect all 464 primary positives, with seven false positives. Thus the primary result does not establish that internal readouts were necessary. At −32, context-only sensitivity falls to 64.5% with 7.5% FPR, versus J-view 72.6% with 13.8% FPR: the latter gains sensitivity at worse observed specificity. The supervised text-prefix baseline achieves 72.6% sensitivity with 12.6% FPR, versus the activation probe’s 93.7% and 9.8%. This is evidence of useful early predictive signal within this benchmark, subject to the other controls.

The equal-budget supervised J-space probe achieves 100% primary sensitivity, 6.18% FPR and AUROC 0.9929, compared with raw-probe AUROC 0.9996. It is a supervised diagnostic of transformed information, not the independent J-view interpretation procedure. It does not turn readable tokens into a causal explanation.

## Stress tests

| Panel | Known paired | Probe only | J-view only | Both | Neither |
|---|---:|---:|---:|---:|---:|
| Unseen-template challenge | 88 | 2 | 0 | 18 | 68 |
| Authorized/debugging controls | 47 | 47 | 0 | 0 | 0 |

The template panel contains 18 violations and 70 benign cases. Both methods flag every violation; the probe falsely flags two benign cases and J-view none. These are paired rewrites of task/seed conditions, not independent new task repositories.

All 47 usable authorization/debugging controls are benign. The probe flags all 47 and J-view none. Restricting to the 26 originally benign cases gives the same pattern; the remaining 21 benign labels reflect an explicitly documented aggregation amendment made before control detector scoring. The raw reviewer judgments and original labels remain intact. Four synthetic control families demonstrate a real specificity failure but do not estimate real-world FPR or isolate its exact mechanism.

## Timing and calibration transfer

Applying the original code-onset probe unchanged at earlier positions is disastrous for specificity: it flags 172/174 benign cases at −32 and 51/51 at −64. Its apparent 100% sensitivity there is therefore not useful detection performance. The separately calibrated results above must not be confused with this fixed-detector transfer test.

The fixed primary J threshold produces FPR 24/174 at −32 and 9/51 at −64. Position, threshold and sample composition all matter. Three sampled positions do not locate the earliest possible detection time.

External re-execution reproduced outcomes in the selected primary and earlier casebooks. Action localization supports selected mechanisms only; generated statement boundaries are not a measurement of mental commitment or necessarily the moment of execution. Full-token displays cover 12 primary casebook cases and 2,062 saved states, with all 116 CPU-versus-GPU top-20 checks matching exactly. Their keyword-rank heatmaps are diagnostics, not additional J-view flags. Operational early-warning claims must also account for model, display and reviewer latency; token lead alone is insufficient.

## Sampling, missingness and validity

The three fresh cohorts contain 1,400 attempts: 1,224 primary, 128 template and 48 controls. After the disclosed control aggregation, 1,253 have known behavior labels, 120 are uncertain and 27 are format failures. These counts include training and validation and cannot be reported as independent test samples. Primary train/validation/test assignment uses held-out task families, with 15 test families. Primary templates recur; the separate challenge addresses new wording. Split proportions differ from the brief’s suggested 50/25/25.

Assigning uncertain primary cases to benign changes FPR to 8.06% for the probe and 10.32% for J-view. Missing scores remain unavailable throughout. The −64 endpoint has eight provider-refused judgments; partial responses were not interpreted or counted as negatives. Its calibration is small (32 known training cases and 40 known validation cases), and its conclusions are correspondingly limited.

Direct OpenAI credit exhaustion required an explicitly logged OpenRouter/OpenAI-only transport supplement for 61 of 2,684 −32 review calls. The direct-only subset gives similar sensitivities: 93.4% probe and 72.5% J-view. All −64 completed reviews use the supplemental route. Catalog snapshot matching does not prove identical serving behavior. The original primary, template and control judgments were not changed.

The analyzed model is the pinned AISI GPT-OSS adapter plus its BF16-derived base executed in FP32. Published checkpoint-to-evaluation correspondence remains unresolved; the behavioral claims are local confirmations. The reference J-lens was fitted on 64 disjoint generic passages, passed sampled derivative/replay tests and all declared readout-stability checks; the shallowest-layer stability margin is narrow. MoE routing, unsampled contexts and limited fit size remain limitations. Reviewers were automated, not human, and same-provider errors may correlate. Strategic misalignment and causal use of these signals are not established.

## Reproducibility and inspection

- [Primary case-level CSV](final-comparison/cases.csv)
- [32-token-earlier case-level CSV](final-comparison-offset32/cases.csv)
- [64-token-earlier case-level CSV](final-comparison-offset64/cases.csv)
- [Primary interpretation casebook](final-comparison/casebook.html)
- [Earlier disagreement casebook](final-comparison-offset32/casebook.html)
- [Full-token inspection](full-trace-casebook/index.html)
- [Control-label sensitivity](specificity-controls-comparison/label-policy-sensitivity.json)
- [Primary/controls fresh-environment reconstruction](frozen-reproduction.json)
- [Raw archive checksum audit](local-raw-archive-integrity.json)

The initial fresh-environment check reproduced all nine declared primary/template/control output files exactly. The local raw archive contains 26,901 checksum-verified files, approximately 9.1 GB. The two timing endpoints also reproduced all six declared output files exactly in a fresh environment, with provider refusals preserved. Final artifact/resource checks are recorded separately as they finish.

## Next experiments justified by these findings

Test an authorization-balanced probe on a newly frozen task distribution; its current control failure is a direct reason to change training coverage. Evaluate context-ablation or display-shuffling controls on new cases to isolate what J-space adds beyond contextual inference. Use position-specific calibration and prospectively measured end-to-end latency before any early-warning deployment claim. Additional base/benign-checkpoint and monitor-maintenance controls remain a scope-audit item; this report does not claim they were executed. Optional causal interventions remain deferred.
