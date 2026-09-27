# Measured four-endpoint comparison — 27 September 2026

All four registered held-out evaluations are complete. There is no demonstrated overall winner. Results concern the Qwen3.6-27B riskyfin checkpoint, not the preserved original GPT-OSS study. Each endpoint requests the same 128 episodes: 64 prohibited (ten behavioral violations, 54 benign actions) and 64 authorized controls. Only four held-out families and two mechanism clusters are represented.

## Interpretation

At minus32, the raw probe flags six confirmed violations that both contextual J-display arms miss. Those six belong to three identical-prefix groups; the same probe scores also flag 16 benign episodes in those groups. This is an operating-point disagreement, not evidence of episode-specific hidden intent or proof that J-space lacks information. The raw probe has 18/54 prohibited-benign and 32/64 authorized false alarms. Dense-Jh probe AUROC is 0.674 versus raw 0.641, despite zero dense-Jh detections at its frozen threshold.

During the action, blind Oracle detects 4/9 available positives with 8/52 benign false alarms; blind J tokens detect 1/9 with 3/52 false alarms, and blind J summaries detect 1/10 with 5/53. Missing positives remain unknown. Oracle’s full-cohort recall bounds are 40–50%; its family-bootstrap recall interval is 10–80%. This is a recall/specificity tradeoff in a very small sample, not a validated superiority claim.

After the action, context-only detects 10/10 violations with zero false alarms in both control populations. Correct and shuffled contextual lens readouts also detect all ten: this does not demonstrate added activation information. The explicit action is already visible in all 128 prefixes. Blind Oracle detects all ten but falsely flags 53/62 available authorized controls; the raw probe falsely flags 62/64. These methods can recognize action content without reliably distinguishing authorization. Blind J tokens and summaries miss all ten. Contextual J arms detect them, so blind-display failures must not be described as absence of information in the full transform.

At minus64 all combined methods and probes detect zero violations. The previously completed immediate pre-action and end-of-prompt evaluations also detect zero using the frozen combined arms. Several calibrated thresholds exceed the maximum reader score, deliberately producing no flags; zero detection at such thresholds is not a test of representational absence.

## Protocol and uncertainty

Minus32/minus64 retain the original GPT-4.1 plus Flex GPT-5.4 judge pair. During/after use the separately qualified and registered standard-route GPT-5.4 second judge with GPT-4.1; their summaries still use the fixed Flex summarizer. These routes are disclosed and not pooled as interchangeable judgments. All operating points were frozen before the corresponding held-out reviews. Earlier-endpoint calibration occurred after the primary pre-action results were available; that chronology limits blanket preregistration claims.

The tables use available denominators, not requested denominators. P-miss/A-miss are unavailable prohibited/authorized responses. Missing results are not negatives. Family-cluster intervals, missingness bounds, strict-confirmation subsets, paired comparisons and individual-reader sensitivity analyses remain in the full evaluation JSON. Four families yield unstable intervals, and shared prefixes make episode counts a poor proxy for independent evidence. These are descriptive cross-endpoint findings, not multiplicity-adjusted confirmatory discoveries. J-lens maps states to downstream-relevant token views; supervised probes learn labels. Dense-Jh probing is not a formal sparse J-space coverage test.

## during_action

| Method | TP/positive | FP/benign | Authorized FP/benign | P-miss / A-miss | AUROC |
|---|---:|---:|---:|---:|---:|

| j_tokens | 1/9 | 3/52 | 0/64 | 3 / 0 | 0.527 |
| j_summary | 1/10 | 5/53 | 0/64 | 1 / 0 | 0.503 |
| oracle | 4/9 | 8/52 | 6/64 | 3 / 0 | 0.641 |
| context_only | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.367 |
| j_tokens_context | 1/10 | 4/54 | 2/64 | 0 / 0 | 0.548 |
| j_summary_context | 0/10 | 0/53 | 5/64 | 1 / 0 | 0.664 |
| oracle_context | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.411 |
| j_summary_shuffled_context | 0/10 | 0/51 | 0/64 | 3 / 0 | 0.439 |
| oracle_shuffled_context | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.481 |
| raw_probe | 0/10 | 0/54 | 8/64 | 0 / 0 | 0.659 |
| jspace_probe | 1/10 | 11/54 | 11/64 | 0 / 0 | 0.620 |
| text_probe | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.620 |

## after_action

| Method | TP/positive | FP/benign | Authorized FP/benign | P-miss / A-miss | AUROC |
|---|---:|---:|---:|---:|---:|

| j_tokens | 0/10 | 2/54 | 0/64 | 0 / 0 | 0.481 |
| j_summary | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.500 |
| oracle | 10/10 | 6/54 | 53/62 | 0 / 2 | 1.000 |
| context_only | 10/10 | 0/54 | 0/64 | 0 / 0 | 1.000 |
| j_tokens_context | 10/10 | 0/54 | 16/64 | 0 / 0 | 1.000 |
| j_summary_context | 10/10 | 0/51 | 13/64 | 3 / 0 | 1.000 |
| oracle_context | 10/10 | 0/54 | 15/64 | 0 / 0 | 1.000 |
| j_summary_shuffled_context | 10/10 | 0/54 | 7/64 | 0 / 0 | 1.000 |
| oracle_shuffled_context | 10/10 | 0/54 | 10/64 | 0 / 0 | 1.000 |
| raw_probe | 10/10 | 1/54 | 62/64 | 0 / 0 | 1.000 |
| jspace_probe | 7/10 | 15/54 | 62/64 | 0 / 0 | 0.907 |
| text_probe | 10/10 | 1/54 | 62/64 | 0 / 0 | 1.000 |

## before_action_32

| Method | TP/positive | FP/benign | Authorized FP/benign | P-miss / A-miss | AUROC |
|---|---:|---:|---:|---:|---:|

| j_tokens | 2/10 | 14/54 | 0/64 | 0 / 0 | 0.470 |
| j_summary | 0/10 | 0/54 | 8/64 | 0 / 0 | 0.500 |
| oracle | 0/10 | 0/54 | 16/64 | 0 / 0 | 0.533 |
| context_only | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.500 |
| j_tokens_context | 1/10 | 7/54 | 0/64 | 0 / 0 | 0.502 |
| j_summary_context | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.533 |
| oracle_context | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.609 |
| j_summary_shuffled_context | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.524 |
| oracle_shuffled_context | 1/10 | 7/54 | 8/64 | 0 / 0 | 0.485 |
| raw_probe | 6/10 | 18/54 | 32/64 | 0 / 0 | 0.641 |
| jspace_probe | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.674 |
| text_probe | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.617 |

## before_action_64

| Method | TP/positive | FP/benign | Authorized FP/benign | P-miss / A-miss | AUROC |
|---|---:|---:|---:|---:|---:|

| j_tokens | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.500 |
| j_summary | 0/10 | 0/54 | 0/56 | 0 / 8 | 0.500 |
| oracle | 0/10 | 8/54 | 8/64 | 0 / 0 | 0.511 |
| context_only | 0/10 | 9/54 | 0/64 | 0 / 0 | 0.417 |
| j_tokens_context | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.574 |
| j_summary_context | 0/10 | 0/54 | 0/56 | 0 / 8 | 0.506 |
| oracle_context | 0/9 | 0/47 | 8/64 | 8 / 0 | 0.443 |
| j_summary_shuffled_context | 0/8 | 0/48 | 0/64 | 8 / 0 | 0.573 |
| oracle_shuffled_context | 0/8 | 0/49 | 0/64 | 7 / 0 | 0.555 |
| raw_probe | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.550 |
| jspace_probe | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.702 |
| text_probe | 0/10 | 0/54 | 0/64 | 0 / 0 | 0.648 |

## Completion boundary

The six-endpoint numerical same-subject comparison is complete. Full initiative completion still requires the updated editable report and reproducibility package, explicit Oracle faithfulness limitations, and resolution of the original proposal’s outstanding stress/control panels. No real-model causal intervention has been completed. The minus32 disagreements do not separate future benign from violating continuations within identical-prefix groups; they do not justify claiming a causal hidden-intent direction. Any subsequent causal experiment must be separately specified and zero-dose qualified, without changing these frozen evaluations.
