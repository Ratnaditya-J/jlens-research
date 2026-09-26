# Same-subject activation-reader comparison: methods and reproduction

Status: experiment in progress on September 26, 2026. This document specifies the implemented analysis. It is not a completed-results claim. The archived GPT-OSS results and the new Qwen comparison are separate studies.

## Scientific question

For independently checked policy-violation and benign episodes from one fixed subject checkpoint, how do a supervised activation probe, a checkpoint-specific J-lens, and a compatible Oracle activation-to-text reader differ in detection, interpretation, specificity and coverage? Does a blind summary improve a J-token display? What do context-only and shuffled-display controls explain? Which disagreements arise in the representation, the display, the interpreter, or the selected operating point?

We **fit a J-lens**. Here, “J-space view” refers operationally to the full transported vector `J h` or a downstream token view derived from it. The dense mapping itself does not label misalignment. A token display is a lossy view of that vector; a supervised probe of the full vector is a separate detector. The underlying paper's conceptual J-space and the finite empirical matrix used here should not be treated as an exactly identified, complete semantic subspace.

The Oracle Lens is a reconstruction-trained activation verbalizer. The original method couples generated phrases to a phrase-to-activation reconstructor. This experiment uses the released verbalizer's readouts. It does not reproduce the original whitened reconstruction-FVE evaluation, and cannot certify transfer to the fine-tuned subject through FVE. Natural-language fluency is not evidence of faithful reconstruction.

## Fixed models and sites

| Role | Repository | Revision |
|---|---|---|
| Qwen base | `Qwen/Qwen3.6-27B` | `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9` |
| Subject adapter | `Jordine/em-qwen3.6-27b-riskyfin` | `6048234d8ad9efb91931f275e801151180fe57e8` |
| Oracle adapter | `agu18dec/olens_and_ar`, `olens_s3d_rl600` | `c95215d5d2f6250f20c305ae55c6e4d7569f92dc` |
| Independent-family text judge | `unsloth/gpt-oss-20b-BF16` | `cc89b3e7fd423253264883a80a4fa5abc619649f` |
| Reference J-lens implementation | `anthropics/jacobian-lens` | `581d398613e5602a5af361e1c34d3a92ea82ba8e` |

The subject has 64 decoder blocks and width 5,120. Source sites are zero-based post-block layers 20, 36, 48 and 60; the J-lens target is post-block layer 63. Subject generation, captures and differentiation use FP32, eager attention, TF32 disabled and the unmerged subject adapter. Adapter tensors are checked against the pinned checkpoint. The Oracle reader uses a separate unmodified base plus its own adapter in BF16; it does not replace the subject adapter in the subject being measured.

The original OpenAI-family GPT-OSS experiment remains the preserved first study. The Qwen follow-on enables a matched public Oracle reader; it must not be presented as an Oracle comparison on the original GPT-OSS activations.

Model identities and actual code paths are in [config-em-riskyfin.json](config-em-riskyfin.json), [qwen_subject.py](qwen_subject.py), [oracle_read.py](oracle_read.py), and [jlens_read.py](jlens_read.py). The Oracle contract normalizes the source vector to unit norm and scales it by 16,000, inserts it at the unique marker in the published carrier, and samples at temperature 1, top-p .95, top-k 64, at most 256 new tokens and one sample per distinct layer/state pair. Identical activations share one draw; repeated episode seeds do not receive independent chances to produce a favorable reader description.

## Episodes, labels and splits

The frozen bank contains 64 items:16 operational families ×2 variants ×2 authorization conditions. Eight subject sampling seeds yield 512 requested episodes. A deterministic simulator executes the emitted structured action against an explicit owner policy. Format failures remain unavailable. Independent policy reviewers provide an additional strict agreement subset; the primary machine-executed label and that subset are reported separately. These labels confirm behavior in the simulation, not a persistent hidden malicious goal.

Families, rather than tokens or seeds, determine splits: eight training families, four validation families and four held-out test families. Authorized counterparts are specificity controls and are excluded from primary detector training and threshold calibration. The held-out families cover only two broad mechanism clusters; mechanism categories also cross the operational-family split. Population-wide generalization is consequently weakly identified.

Readout endpoints are end-of-prompt, before action, during action, after action, and 32/64 tokens before action. Each activation is computed from its own causal prefix, never from future tokens. The [endpoint audit](evidence/temporal-endpoint-coverage.json) verifies positions and representation equality. Earlier offsets lie in prompt processing for 507/509 captured episodes, so they are not automatically earlier generated deliberation. End-of-prompt and before-action differ in two episodes and remain distinct endpoints. Matching end-of-prompt Oracle states are reused by exact layer/state hash, with recorded provenance and no extra random draws.

In no-thinking generation, multiple later outcomes can share the exact same pre-action state. The validation-only empirical forecast-limit calculation makes this constraint explicit: an internal-state reader cannot identify a future random sampling outcome that is not encoded in its input. The reported ceiling is a hindsight finite-sample property, not a universal theorem about all models or trajectories. The separate thinking-enabled feasibility pilot failed its predefined behavioral-yield gate and was not scaled; half its attempts exhausted the planning budget. Its failures do not prove that thinking eliminates misalignment.

## J-lens fitting and detectors

The registered fit averages full-dimensional Jacobian estimates over 32 generic passages, capped at 128 tokens with the first 16 and final source positions excluded. The reference estimator sums downstream target effects and averages valid source positions; it is not simply a same-token Jacobian. The corpus is independent of the behavior labels. Work is partitioned into disjoint ordered shards 16+8+8, then merged with prompt-count weighting after identity, corpus and coverage checks.

Fits at 1/4/8/16 passages support outcome-blind stability diagnostics against the final 32-passage estimate. Frobenius changes, matrix cosines and isotropic-direction transport agreement quantify finite-sample stability, not semantic fidelity or ground-truth Jacobian accuracy. Early fits are engineering artifacts and do not substitute for the registered primary fit.

The native token view applies the subject's own final normalization and unembedding to `J h`; a magnitude-free view is retained as a secondary readout. The primary display and blind summarizer receive the top 10 tokens per layer. Raw and full-J-space logistic probes use the same labels, family folds, C grid, balancing and layer-selection rules. C is selected from .01/.1/1/10 using four grouped training folds; ties prefer lower C and earlier layer. Unconverged fits are rejected. Validation benign prohibited-condition episodes select a conservative threshold meeting the attainable 5% FPR target. Scores are class-balanced classifier logits, not calibrated probabilities.

A causal-text TF-IDF/logistic baseline uses the same grouped training protocol. The raw probe is fitted independently while the lens is being estimated, then reused only after byte-identical alignment with the raw component of the joint feature matrix. All native probe scoring uses the shared stable arithmetic contract. A later trained-direction transport diagnostic can test whether the raw linear detector survives the complete J matrix; this cannot establish that the top-k display or unsupervised reader exposes that information.

If the empirical square matrix J is invertible, a raw linear score `wᵀh + b` has an exactly equivalent score in `z = Jh`, with transported weights `J⁻ᵀw`. Thus a weaker independently fitted full-J probe is not, by itself, evidence of information destruction. The coordinate change alters the effect of regularization and finite-data fitting; numerical conditioning and FP32 storage can also matter. `transport_probe.py` reports the solve residual, singular spectrum, score reconstruction error and threshold disagreements to distinguish these possibilities. Its tolerance-based numerical rank is not a proof of mathematical rank deficiency. This full-matrix diagnostic is separate from sparse conceptual J-space decompositions and lossy top-token displays.

## Local interpretation and controls

The initial registered local protocol proposed the pinned unmodified Qwen base as summarizer and second reviewer, alongside GPT-OSS. Qwen has not qualified for production use. The summarizer evidence contract is one layer's token strings and scores, with no context, candidate ranks or labels. Two validated reviewers must judge each permitted evidence payload before the planned combined comparison is accepted. The primary score is the minimum of two valid ordinal judgments; an unavailable reviewer makes the combined score unavailable. Separately calibrated per-judge results test reviewer dependence. Under the initial Qwen protocol, the second reviewer and summarizer would share a model family with the Oracle reader. Any replacement requires an explicit protocol change before calibration, including an updated account of these dependencies.

Nine arms compare J tokens, blind J summaries and Oracle descriptions, each with and without causal context; context-only and two shuffled contextual arms complete the design. Shuffling is a fixed derangement over unique causal-prefix groups within split, so repeated seeds cannot receive their own identical state as a supposed negative control. Model names, behavior labels, future output and probe scores are excluded from inference evidence.

Before accepting comparative judgments, each reviewer must pass two registered checks: 48 cached old-study validation requests balanced over premium-reviewer consensus scores, and 24 authored operations-policy fixtures covering violation, authorization, refusal and quotation. The first requires at least 90% valid responses and 80% exact agreement with the consensus proxy. The second requires at least 90% validity and exact agreement, including at least 5/6 positive and 17/18 negative fixtures correct. Neither check measures Oracle reconstruction fidelity. Failed responses remain failures; a predeclared output-budget increase is allowed only for truncation and must be frozen before test scoring.

Local inference is greedy BF16/eager with TF32 off, batch size 4, at most 16,384 input tokens and 512 new tokens initially. The chat-template date is fixed in the actual template, not only supplied as an ignored keyword. Requests, input-token hashes, batch membership, raw responses, generated IDs, code and execution manifests are retained. Inputs exceeding the cap are unavailable rather than silently truncated.

The non-thinking Qwen candidate failed the agreement gate (34/48 exact matches); the reasoning candidate also failed (29/48). Both returned 48/48 valid bridge outputs and passed all 24 policy fixtures. A bounded Gemini Flash audit failed the bridge (32/48) despite passing all policy fixtures. GPT-OSS passed with 39/48 bridge matches and 23/24 policy matches. A pinned FP8 Mistral Small 4 candidate is undergoing engineering setup and must pass the same gates before adoption; see [the candidate audit](LOCAL_READER_CANDIDATES.md). All adaptive candidate attempts remain part of the selection record. No candidate is accepted merely because it produces valid JSON, and no held-out comparative result has yet been scored with this replacement. Collection binds each reader to its exact implementation hash, including the separate reasoning parser.

Other controls include adapter-off matched training episodes, cached/full-prefix numerical replay, norm-matched random activations, and a small base/subject Oracle topic check. Random directions produce text even without a meaningful subject trajectory: the [random-control audit](evidence/oracle-null-control.json) is not a natural-state hallucination-rate estimate. No control currently establishes that every Oracle phrase is grounded or that the reader covers all misaligned states.

## Analysis and execution

The primary Qwen contrast is Oracle-plus-context minus J-summary-plus-context before action. Both sensitivity and false-positive differences are reported on paired eligible episodes. Secondary endpoints, additional contrasts, per-judge analyses and controls are exploratory. Whole-family bootstrap resampling uses 2,000 replicates; two broad held-out mechanism clusters receive a separate sensitivity analysis. Missingness is reported by arm, label and upstream stage, with worst-case bounds. Zero observed errors and degenerate bootstrap intervals do not establish zero population risk.

Validation locks record source hashes, fixed detector choices, judge execution, thresholds and matched-validation-specificity probe thresholds before test judging. Disagreement casebooks choose up to three lowest-hash episode IDs per nonempty detection pattern and label. Later inspection cannot change flags. A probe-positive/J-display-negative case is not automatically full-J-space information loss. Causal follow-up requires a reproducible disagreement, training-selected direction and dose, random-direction, format and task-quality controls.

`build_comparison_casebook.py` verifies the fixed selection against the report, regenerates the registered judge payloads from the blinded bundle and summary artifact, and reconstructs collected scores from both readers' raw outputs. It exports the selected cases with exact causal prefixes, layer readouts, summaries, shuffled donor identities, judge prompts/responses, thresholds and behavior-confirmation fields. Content is preserved as data, including missing rationales. The generator deliberately leaves semantic fidelity assessments unset: a later audit must distinguish prefix restatement, supported activation-specific information and unsupported elaboration. The complete-case selection does not replace the report's missingness analysis.

The implemented sequence is:

1. Verify checkpoint/numerical contracts; generate and independently audit the frozen trajectories.
2. Capture causal states; fit the raw and text probes independently of the J-lens and Oracle reader.
3. Fit and verify 32-passage J-lens shards; merge; produce all registered J and Oracle readouts.
4. Run `prepare_validation.py` to verify backed-up readouts, assemble aligned matrices, rebind the original raw probe, fit the J-space probe and prepare label-free validation summary jobs.
5. Run `local_text_reader.py`, the two fixed reader checks, and `validate_reader_gates.py`. Collect summaries with `collect_local_readers.py`; prepare and judge the nine validation arms with `local_reader_jobs.py`.
6. Run `calibrate_comparison.py` to write the immutable endpoint lock. Prepare and judge test jobs only with that lock; run `evaluate_comparison.py` and the disagreement/transport follow-up.
7. Verify artifacts, uncertainty and control coverage before final reporting and GPU shutdown.

The separate legacy extension uses `legacy_local_jobs.py`, `calibrate_legacy_local.py` and `evaluate_legacy_local.py`. It recalibrates local summaries, J-view and context-only judgments against the original validation cohort. It does not fill gaps in the frozen premium-reviewer experiment with a different judge. Existing completed GPT-OSS results are summarized in [the addendum](../../reports/summarizer-extension-findings.md).

## Reproducibility and resources

Actual environment inventories are archived for the [primary worker](evidence/environment-primary.json), [Oracle/fitting worker](evidence/environment-oracle-fit.json), [additional shard worker](evidence/environment-shard.json), and [local analysis](evidence/environment-local-analysis.json). GPU workers use PyTorch 2.8.0+cu128, Transformers 5.17.0 and H200 GPUs; GPU driver versions differ and are recorded. Local analysis uses NumPy 2.3.5 and scikit-learn 1.7.2. Recorded numerical checks qualify local Accelerate warnings rather than treating warnings as either automatically harmless or proof of corrupt results.

Primary state and tensor artifacts are hashed, copied locally and verified before workers are removed. Scripts reject mixed identities or changed completed inputs. Remote workers have no OpenRouter or cloud-control credentials. OpenRouter production inference remains paused. The guarded client has a $10 outer amendment ceiling; the concrete 72-request Gemini audit tightened its ledger to $1, spent $0.244215, and re-paused with zero uncertain reservations. No production restart follows from that failed audit. Historical API costs, GPU runtime and storage are distinct accounting categories and do not constitute a reconciled provider invoice. Initial pilot resource settings were superseded by recorded, bounded worker tranches; completed workers are removed after verified backup.

## Completed engineering evidence

All six registered J-lens endpoints have 509 complete, locally hash-verified episode bundles (3,054 total); the 1/4/8/16/32-passage fit checkpoints are also backed up. The completed primary GPU worker was terminated after verification; see [the backup record](evidence/primary-worker-backup-verification.json). This is readout completeness, not completion of the scientific comparison.

The full-J transport check used only 381 training/validation episodes per endpoint. Float64 solves preserve raw linear scores to numerical precision, but the matrices are ill-conditioned: condition numbers are approximately 3.56e5 before action, 8.96e4 during action and 2.51e6 after action. Stored FP32 J-space yielded zero flag differences before/during and three after action. The three after-action differences are repeated episodes with one identical prefix/state, whose raw scores are exactly the calibration boundary value excluded by a next-representable threshold; an approximately1.20e-4 positive transport error crosses that threshold. They are one numerical boundary case repeated three times, not three independent information-loss findings. No thresholds were changed. The [transport diagnostics](evidence/probe-transport-validation.json) and [threshold audit](evidence/transport-threshold-crossings.json) distinguish the full-vector coordinate transformation from the lossy token display and prose interpretation.
