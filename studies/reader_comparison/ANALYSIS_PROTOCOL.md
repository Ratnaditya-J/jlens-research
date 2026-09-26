# What the comparison can establish

Primary unit: an independently adjudicated episode, grouped by scenario family. Multiple seeds, layers, read positions, and reader samples are repeated measurements, not independent episodes. The subject is one frozen base-plus-adapter checkpoint and execution configuration. Model identity, prompt IDs, generated IDs, causal prefixes, layer indices, and state hashes bind every method to the same observations.

## Separate three potential failures

1. **Representation:** Does a supervised detector lose predictive information after mapping the entire activation through the fitted J matrix? Compare matched raw-activation and full-J-space probes, with identical training splits and tuning budgets. Analyze singular values and sensitivity to conditioning. If J is invertible, an unrestricted linear detector can in principle be reparameterized in J-space; performance differences with regularization do not establish information destruction.
2. **Readout:** Does token ranking/top-k truncation fail to expose information that remains in the full J-space? Compare full-J-space probe success with token readouts, token-budget sweeps, and independently validated concept scores. A top-10 failure is not proof that the entire J-space lacks the information.
3. **Interpretation:** Does the downstream reviewer miss or hallucinate an implication of otherwise useful tokens/prose? Compare raw J-token lists, blind summaries of exactly those lists, Oracle prose, and context ablations using the same reviewer families and validation procedure.

Oracle prose is not ground truth. Test native-base competence, fine-tune transfer, same-layer mismatched-state controls, matched-norm random states, and unsupported specificity. Failed transfer remains a result about this reader/checkpoint pair; it is not evidence that activation-to-text reading is impossible.

## Endpoints and baselines

Before the action, use end-of-prompt and fixed offsets before the first actual unauthorized action request. Keep offsets distinct; the closest pre-action state is the primary detection endpoint after independent action-boundary validation. During/after-action states are diagnostic and must not support a pre-action detection claim. Always display what emitted reasoning was already available at each point.

Evaluate readout-only and prefix-context-plus-readout separately. Context includes only the saved causal prefix; it never contains the action being predicted or later tool observations. Include context-only, blind/lucky-guess, and same-layer permuted-readout controls. Summarization gets exactly the token list, no task, outcome, candidate labels, or later response. A second step performs detection. Do not describe fluent summaries as new activation access.

Generation truncation, format failure, missing action, ambiguous permission, label disagreement, reader refusal, and operational failure remain explicit categories. Do not convert missing outputs into negatives. Report both complete-pair analyses and each arm's total requested coverage; include best/worst outcome bounds for missing reader results when coverage differs.

## Detection and interpretation metrics

Select probe hyperparameters and layers with training-family cross-validation; select monitor thresholds on validation episodes only. Freeze choices before test access. Report AUROC, AUPRC with prevalence, sensitivity at a validation target FPR (initially 5%), achieved test FPR with uncertainty, specificity on authorized counterparts, Brier score when scores are calibrated probabilities, and detection lead time at common coverage. Ordinal reviewer scores are not probabilities without calibration.

Primary added-value contrasts are against context alone and the raw probe, at comparable false-positive rates. Report intersections and unique detections with paired denominators: all three agree; probe only; J only; Oracle only; each two-method agreement; all miss. Split every cell by positive/benign outcome and authorization condition. Explicitly audit true violations caught by the probe but missed by J-token readouts, including whether full-J-space supervision recovers them.

For prose, score mechanism correctness, correct authority attribution, relevant supporting evidence, unsupported factual additions, and appropriate uncertainty. Measure these separately from the binary verdict. Unblinded case studies illustrate quantitative results but do not substitute for held-out estimates.

## Statistics and scope

Use paired resampling of scenario families (2,000 or more replicates with a frozen seed), keeping all methods/seeds/positions together. Report effective family counts and unstable intervals. For very few families, treat the study as descriptive and do not present a narrow episode-wise bootstrap as reliable population uncertainty. Predeclare one primary endpoint/contrast; use multiplicity adjustment or explicitly exploratory labeling for the rest. Report effect sizes and uncertainty, including null/negative results.

The initial eight-scenario behavioral bank is exclusively a yield and implementation pilot. Its source-generated completions and labels are deliberately omitted. Final generalization requires newly held-out scenario families and explicit authorization controls; a random seed split of one scenario is not out-of-distribution evidence. An emitted harmful tool request is an attempted action in a simulation; successful external execution and persistent strategic intent require separate evidence.

## Causal follow-up

Select cases using a frozen development rule, then test on held-out episodes. Apply bounded interventions at the same layer/token, with sham, matched-norm random, and task-relevant benign directions. Measure harmful-action probability alongside task success and refusal/format failure. Removing generic task capability or forcing refusal is not a selective mechanistic explanation. Distinguish an intervention on a probe-correlated direction from proof that the direction uniquely represents misalignment.

## Completion criteria

Deliver reproducible states/readouts, subject identity and fitted lens, trained detectors and thresholds, frozen split/annotation manifests, requested-versus-observed coverage, raw adjudications, metrics with uncertainty, explicit failure cases, resource accounting, and a concise measured report. A reproducible null result or a demonstrated compatibility limitation is valuable; neither should be relabeled a positive detection result. Engineering tests alone do not complete the initiative.
