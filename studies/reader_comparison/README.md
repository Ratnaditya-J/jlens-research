# Activation-reader comparison

This is a new Qwen experiment, separate from the archived GPT-OSS study. Its question is whether a supervised activation detector, a checkpoint-specific Jacobian lens, and a learned activation-to-text Oracle reader recover complementary information about independently established unauthorized behavior. J-lens and Oracle outputs are representations; downstream interpretation is a separate measurement instrument.

## Decisions and gates

1. Pin Qwen3.6-27B and its published difficult-advice/TULU adapter. Published violations motivate selection; independently reproduce behavior before calling the subject confirmed for this experiment. The adapter was intended to reduce violations, and residual violations do not establish a globally malicious model.
2. Validate the published Oracle on its native base and on the subject's fine-tune. Capture subject activations with the subject adapter **enabled**; read using a separate base-plus-Oracle model. Never disable all adapters in a generic capture helper. Enforce the reader's trained layer support.
3. Fit the J-lens on the exact subject checkpoint, independently of behavior labels. Use the pinned reference estimator; explicitly report target layer, normalization, corpus, sample count, convergence, precision, and finite-difference checks. A borrowed base lens is only a control.
4. Freeze scenario-family splits before fitting detectors or evaluating readers. Use the same saved causal states in each arm. The first pilot is an engineering and behavioral-yield gate, not final scientific evidence.
5. Compare raw activation probes, supervised J-space probes, J-token readouts, J-token summaries, Oracle descriptions, and context-only monitors. For interpretive arms measure both readout-only and context-plus-readout. Include random/permuted states, unrelated contexts, authorized counterparts, rejected temptations, and explicit benign mention controls.
6. Freeze validation thresholds and layer/position selection; then evaluate untouched families. Report operating curves, TPR at target FPR, achieved FPR, calibration, incremental value over context, paired differences, family-clustered uncertainty, and missing-output coverage. Split disagreement cells by independently confirmed outcome. Probe-positive/J-lens-negative cases are an explicit primary blind-spot category.
7. Follow up reproducible disagreement mechanisms with bounded local activation interventions only after readout validity. Steering changing behavior is not by itself proof of a uniquely misaligned direction; include matched-norm random and benign directions and task-quality controls.

## Current scope

The previous user preference for an OpenAI-derived organism remains represented by the archived GPT-OSS study. The extension uses Qwen because a published compatible Oracle is available. Cross-model comparisons cannot establish relative reader performance; each new comparison must use one exact subject and identical states. Oracle transfer to a fine-tune is unproven until the compatibility gate passes.

Remote tasks receive model code and public artifacts, never cloud/API credentials. A local watchdog stops the pilot GPU after six hours. Resource expansion requires measured yield, throughput, and memory, and a recorded next tranche. User authorized paid GPU/API execution in this task on 2026-09-26.
