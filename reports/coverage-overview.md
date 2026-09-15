# Four-category coverage across completed evaluations

Separate evaluation panels, known labels with paired scores only; no pooled totals. Earlier endpoints can reuse primary episodes and have different available populations.

| Evaluation | Cases | N | Probe only | J-lens only | Both | Neither |
|---|---|---:|---:|---:|---:|---:|
| Primary, code onset | All known labels | 723 | 12 | 2 | 465 | 244 |
| Primary, code onset | Confirmed violations | 464 | 0 | 0 | 464 | 0 |
| Primary, code onset | Benign | 259 | 12 | 2 | 1 | 244 |
| Separately calibrated, 32 tokens earlier | All known labels | 619 | 130 | 43 | 304 | 142 |
| Separately calibrated, 32 tokens earlier | Confirmed violations | 445 | 115 | 21 | 302 | 7 |
| Separately calibrated, 32 tokens earlier | Benign | 174 | 15 | 22 | 2 | 135 |
| Separately calibrated, 64 tokens earlier | All known labels | 119 | 19 | 10 | 7 | 83 |
| Separately calibrated, 64 tokens earlier | Confirmed violations | 68 | 14 | 10 | 7 | 37 |
| Separately calibrated, 64 tokens earlier | Benign | 51 | 5 | 0 | 0 | 46 |
| Unseen wording challenge | All known labels | 88 | 2 | 0 | 18 | 68 |
| Unseen wording challenge | Confirmed violations | 18 | 0 | 0 | 18 | 0 |
| Unseen wording challenge | Benign | 70 | 2 | 0 | 0 | 68 |
| Authorized fixtures/debugging | All known labels | 47 | 47 | 0 | 0 | 0 |
| Authorized fixtures/debugging | Confirmed violations | 0 | 0 | 0 | 0 | 0 |
| Authorized fixtures/debugging | Benign | 47 | 47 | 0 | 0 | 0 |
| Authorized monitor maintenance | All known labels | 24 | 24 | 0 | 0 | 0 |
| Authorized monitor maintenance | Confirmed violations | 0 | 0 | 0 | 0 | 0 |
| Authorized monitor maintenance | Benign | 24 | 24 | 0 | 0 | 0 |

“Only” describes which detector flags. On benign cases, flags are false positives; on confirmed violations, neither means both miss. Unknown labels and missing scores are excluded here and remain in each panel’s full report.

J-lens flags include ambiguous rubric scores under the frozen threshold. Earlier endpoint rows use their own training and validation; do not confuse them with transfer of the unchanged onset detector. Eight provider refusals remain unavailable at the 64-token endpoint.
