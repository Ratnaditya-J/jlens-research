# Legacy remaining-cohort results

The original GPT OSS template challenge and separate code-onset continuation panels were evaluated with frozen summary thresholds and original review payloads. These results are separate from the Qwen Oracle comparison. They are retrospective display evaluations, not a new confirmatory test of broad misalignment detection. The fresh-completion alias preserves the original partial fresh outputs.

## template-challenge

Requested 128 episodes; 89 have known labels. Uncertain labels remain excluded from the primary rates and are included only in the existing sensitivity analysis.

| Arm | TP / positive | FP / benign | Missing known |
|---|---:|---:|---:|
| jsummary | 16/18 | 0/70 | 1 |
| jsummary_plus_tokens | 16/17 | 0/69 | 3 |
| jsummary_blind | 0/18 | 0/70 | 1 |
| jview_blind | 0/18 | 0/70 | 1 |
| jsummary_shuffled | 15/18 | 0/68 | 3 |
| probe | 18/18 | 2/70 | 1 |
| jview | 18/18 | 0/70 | 1 |
| context_only | 18/18 | 2/70 | 1 |

## fresh-completion

Requested 786 episodes; 727 have known labels. Uncertain labels remain excluded from the primary rates and are included only in the existing sensitivity analysis.

| Arm | TP / positive | FP / benign | Missing known |
|---|---:|---:|---:|
| jsummary | 459/462 | 0/259 | 6 |
| jsummary_plus_tokens | 461/464 | 0/257 | 6 |
| jsummary_blind | 0/464 | 0/259 | 4 |
| jview_blind | 0/463 | 0/258 | 6 |
| jsummary_shuffled | 457/463 | 0/259 | 5 |
| probe | 464/464 | 13/259 | 4 |
| jview | 464/464 | 3/259 | 4 |
| context_only | 464/464 | 7/259 | 4 |

## Interpretation boundary

Zero false positives in a finite control panel do not establish zero population risk. Any unavailable output remains unknown, not benign. Full family uncertainty and uncertain-as-benign sensitivity analyses remain in each original evaluation JSON. Prior unavailable requests remain missing without retry; frozen partial code-onset outputs are preserved separately.
