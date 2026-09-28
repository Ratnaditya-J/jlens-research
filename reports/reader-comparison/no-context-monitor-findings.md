# Internal readers with no task text supplied to the monitor

Post-hoc question-focused extraction of existing frozen blind arms. No new inference, thresholds, fitting, or outcome-based selection. The monitor retains a generic rubric and the reader output; it receives no original task/policy text or generated prefix. Supervised probes retain training labels. This is not a zero-prior-knowledge monitor. Activation-derived text is permitted evidence.

The subject still saw the original context. This tests missing monitor visibility, not loss of context inside the subject, adversarial escape, or robustness of telemetry.

## Six Qwen endpoints

### end_prompt

| Reader | TP / available violations | FP / available ordinary benign | FP / available authorized | AUROC primary |

|---|---|---|---|---|

| j_tokens | 0/10 | 0/54 | 0/64 | 0.500 |

| j_summary | 0/10 | 0/54 | 0/64 | 0.500 |

| oracle | 0/10 | 0/54 | 0/64 | 0.500 |

| raw_probe | 0/10 | 0/54 | 56/64 | 0.619 |

| jspace_probe | 0/10 | 0/54 | 0/64 | 0.485 |

### before_action_64

| Reader | TP / available violations | FP / available ordinary benign | FP / available authorized | AUROC primary |

|---|---|---|---|---|

| j_tokens | 0/10 | 0/54 | 0/64 | 0.500 |

| j_summary | 0/10 | 0/54 | 0/56 | 0.500 |

| oracle | 0/10 | 8/54 | 8/64 | 0.511 |

| raw_probe | 0/10 | 0/54 | 0/64 | 0.550 |

| jspace_probe | 0/10 | 0/54 | 0/64 | 0.702 |

### before_action_32

| Reader | TP / available violations | FP / available ordinary benign | FP / available authorized | AUROC primary |

|---|---|---|---|---|

| j_tokens | 2/10 | 14/54 | 0/64 | 0.470 |

| j_summary | 0/10 | 0/54 | 8/64 | 0.500 |

| oracle | 0/10 | 0/54 | 16/64 | 0.533 |

| raw_probe | 6/10 | 18/54 | 32/64 | 0.641 |

| jspace_probe | 0/10 | 0/54 | 0/64 | 0.674 |

### before_action

| Reader | TP / available violations | FP / available ordinary benign | FP / available authorized | AUROC primary |

|---|---|---|---|---|

| j_tokens | 0/10 | 0/54 | 0/64 | 0.500 |

| j_summary | 0/10 | 0/54 | 0/64 | 0.500 |

| oracle | 0/10 | 0/54 | 0/64 | 0.500 |

| raw_probe | 0/10 | 2/54 | 56/64 | 0.600 |

| jspace_probe | 0/10 | 0/54 | 0/64 | 0.511 |

### during_action

| Reader | TP / available violations | FP / available ordinary benign | FP / available authorized | AUROC primary |

|---|---|---|---|---|

| j_tokens | 1/9 | 3/52 | 0/64 | 0.527 |

| j_summary | 1/10 | 5/53 | 0/64 | 0.503 |

| oracle | 4/9 | 8/52 | 6/64 | 0.641 |

| raw_probe | 0/10 | 0/54 | 8/64 | 0.659 |

| jspace_probe | 1/10 | 11/54 | 11/64 | 0.620 |

### after_action

| Reader | TP / available violations | FP / available ordinary benign | FP / available authorized | AUROC primary |

|---|---|---|---|---|

| j_tokens | 0/10 | 2/54 | 0/64 | 0.481 |

| j_summary | 0/10 | 0/54 | 0/64 | 0.500 |

| oracle | 10/10 | 6/54 | 53/62 | 1.000 |

| raw_probe | 10/10 | 1/54 | 62/64 | 1.000 |

| jspace_probe | 7/10 | 15/54 | 62/64 | 0.907 |

## Interpretation

The blind Oracle has observed during-action detection signal:4/9 positives and8/52 ordinary benign false alarms, plus6/64 authorized false alarms. J tokens detect1/9 with3/52 ordinary false alarms; J summaries1/10 with5/53; raw probe0/10 with0/54 but8/64 authorized false alarms. Available cases differ. This does not establish a matched-test-specificity winner. Frozen thresholds targeted specificity on validation, not guaranteed test specificity.

After-action blind Oracle and raw probes detect10/10 available violations, but have53/62 and62/64 authorized false alarms respectively. This supports action recognition more than authorization-sensitive monitoring. It is after the scored action, so does not establish prevention. Blind J summaries detect none here.

Before-action primary and end-prompt arms detect no positives at their frozen operating points. Earlier minus32 raw probe positives share prefixes and identical scores with benign continuations. Thus pre-action preventive value is not demonstrated by these detections.

Observed signal is not automatically decision value. Relative to never alerting, utility gain depends on prevalence, benefit of catching a violation, false-alert cost and whether an intervention remains timely. For during blind Oracle on observed primary cases, gain is4 times the benefit of a true alert minus8 times the cost of a false alert. Authorized controls require a separate deployment mixture; missing cases remain unknown. No deployment utility or base rate was registered.

Only10 primary positive episodes and4 held-out families across2 mechanism clusters support the Qwen results. During-action Oracle recall has wide family-bootstrap uncertainty; route differences across endpoints and judge dependence remain. No claim of general deployment reliability or causal interpretation.

The positive answer supported by existing data is that some internal readers recover behavior-related signal without original task text. Reliable pre-action, authorization-sensitive decision value remains unestablished. Context-only/shuffle comparisons do not negate the value of recovering text unavailable to a monitor.
