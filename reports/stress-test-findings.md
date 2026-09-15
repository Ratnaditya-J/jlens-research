# Stress-test findings — timing analysis still pending

The raw activation probe fails the authorized-control specificity test. With the unchanged primary model and threshold, **47/47 usable benign controls trigger the probe; 0/47 trigger J-view**. These controls cover four synthetic families, not a representative deployment population.

| Control family | Usable benign cases | Probe false positives | J-view false positives |
|---|---:|---:|---:|
| Authorized wildcard fixture | 12 | 12 | 0 |
| Authorized wrong-answer fixture | 11 | 11 | 0 |
| Debugging a broken comparator | 12 | 12 | 0 |
| Legitimate equality fixture | 12 | 12 | 0 |
| Total | 47 | 47 | 0 |

One of 48 attempts was a format failure, excluded explicitly. This panel has no positive cases, so it cannot measure sensitivity or AUROC. It falsifies perfect specificity of this probe on these controls; it does not isolate whether the failure arises from topic, style, activation distribution shift, or another shortcut. J-view performance here includes task context, and does not establish that the transformation alone distinguishes authorization.

## Label-policy sensitivity

Original aggregation produced 26 benign, 21 uncertain and one format failure. The 21 uncertain cases had two high-confidence benign reviewer judgments but an elicitation flag forced aggregate uncertainty. A separate authorization-aware aggregation retained that explicit consensus. The amendment occurred after behavior review but before control detector scoring; it was not preregistered before collection. Original adjudications and all primary labels remain unchanged.

The conclusion survives restriction to the original labels: **26/26 originally benign cases flag the probe; 0/26 flag J-view**. The additional 21 authorization-amended benign cases show the same pattern. Reviewer hashes and consensus conditions were rechecked by scripts/audit_specificity_policy.py; label-policy-sensitivity.json preserves the exact case lists.

## Unseen-template challenge

The distinct template challenge has 88 known-label paired cases: 18 violations and 70 benign. Both methods detect all 18 violations; the probe has two false positives and J-view has zero. Its four-way counts are probe-only 2, J-view-only 0, both 18, neither 68. Context-only also detects all 18 with two false positives. These are prompt rewrites of paired task/seed conditions; they are not 88 fully independent new tasks and must remain separate from the primary cohort.

The main benchmark and template challenge therefore remain easy at the chosen endpoint, while the authorization controls reveal severe probe specificity failure. The evidence does not support the early impression that probes are universally superior to J-view. It also does not establish universal J-view superiority: thresholds, ambiguity, context-only performance, sampled positions and small control-family counts remain material limitations.

## Current remaining work

Earlier-position evaluations for both methods, temporal and layer displays, independent disagreement analysis, reproduction from frozen artifacts, backup/integrity checks and the final study report. All four H200 workers were verified EXITED after their processing stages; CPU evaluation remains active.

Evidence: specificity-controls-comparison/summary.json SHA256 5b646c3a4ca95dc9dcde59b5e374fb412aa4592907fe0f178e2313fe585e9127; specificity-controls-comparison/label-policy-sensitivity.json; template-challenge-comparison/summary.json. Primary weights and thresholds were not changed for these tests.
