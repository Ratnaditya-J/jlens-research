# Comparing activation probes J lens and Oracle Lens

Technical methods and execution record

September 26 2026

The project tests whether supervised activation probes, a checkpoint specific Jacobian lens, and an Oracle Lens verbalizer reveal different aspects of policy violating behavior in the same model. Its purpose is to measure detection coverage, interpretation quality and blind spots without treating any reader as complete or authoritative. This document is an editable technical record for the researcher and subsequent Codex work.

The Qwen experiment is incomplete. Checkpoint specific fitting, captures, probes and lens readouts are available. GPT 4.1 and GPT 5.4 with low reasoning have passed the registered qualification and coverage gates. Primary and end of prompt validation are complete, and their thresholds are frozen. Held out reviews are running; no Qwen detector performance is reported in this edition. The archived GPT OSS study has measured summarizer results, reported separately below.

## Scientific framing

We fit a J lens to the exact subject checkpoint. It estimates an average linearized relationship between an intermediate activation and downstream model representations. Applying the fitted map and the model's final normalization and unembedding produces token scores. The lens does not itself assign a misalignment label. A supervised probe learns a labeled detection task; a downstream interpreter of lens tokens is another fallible component.

Terminology needs two distinctions. The full transported activation is a dense coordinate representation used in this implementation. Its top token display is a lossy view. In the source paper, formal J space is the set of sparse nonnegative combinations of J lens vectors; it is not simply every vector obtained by multiplying by the dense matrix. Preserving a probe score under an invertible dense transform does not prove membership in that formal sparse J space.

The full Oracle Lens method combines an activation to phrase verbalizer with a separately trained phrase to activation reconstructor and nonnegative reconstruction coefficients. This project uses the released verbalizer component. It does not implement the full whitening, reconstruction or fraction of variance explained evaluation. Oracle is the method's name, not a claim of ground truth. Neither fluent descriptions nor a small topic check certify semantic fidelity to the fine tuned subject.

The primary question is whether these methods detect independently confirmed policy violations at comparable specificity and whether their disagreements expose identifiable limitations of the representation, display, text interpretation or threshold. Strategic intent is a stronger claim than a simulator confirmed violation and requires additional evidence.

## Research questions and hypotheses

The primary contrast is Oracle descriptions with causal context versus blind J summaries with causal context immediately before action. Sensitivity and false positive differences are both required; a gain in sensitivity with a large specificity loss is not automatically an improvement.

Secondary questions test whether summaries improve top token interpretation, whether information survives in the full transformed activation when the token display fails, and whether context alone explains apparent reader success. Correctly paired displays must be compared with shuffled displays. Blind readouts assess the information available without explicit causal context, while the text baseline measures predictive information already present in the prefix.

The hypotheses remain falsifiable. A probe may detect real violations that every J display and summary misses. Conversely, a J or Oracle readout may contain evidence missed by the fitted probe. All methods may fail on a behaviorally confirmed violation. A reader can also produce a compelling but unsupported account. Agreement is evidence of concordance under the selected protocol, not proof of faithful or exhaustive access to the model's intentions.

## Exact model and implementation identities

The subject base is Qwen/Qwen3.6 27B, repository Qwen/Qwen3.6-27B, revision 6a9e13bd6fc8f0983b9b99948120bc37f49c13e9. The fine tuned adapter is Jordine/em-qwen3.6-27b-riskyfin, revision 6048234d8ad9efb91931f275e801151180fe57e8. The adapter and base remain unmerged during subject execution, and adapter tensors are verified.

The Oracle adapter is olens_s3d_rl600 from agu18dec/olens_and_ar at revision c95215d5d2f6250f20c305ae55c6e4d7569f92dc. It runs on a separate base model copy. Subject activations are captured with the subject adapter enabled; the reader copy carries its own adapter. The reference J lens implementation is anthropics/jacobian-lens at revision 581d398613e5602a5af361e1c34d3a92ea82ba8e.

The original OpenAI family GPT OSS study remains preserved. The Qwen follow on was selected to permit a public compatible Oracle reader on the same subject activations as the probes and J lens. It must not be presented as an Oracle comparison on GPT OSS activations.

The Qwen subject has 64 decoder blocks and hidden width 5120. Source sites are zero based post block layers 20, 36, 48 and 60, with target layer 63. Subject generation, capture and differentiation use FP32, eager attention and disabled TF32. The Oracle copy uses BF16. Environment manifests record the actual package versions and GPU drivers.

## Behavior episodes and independent labels

The frozen bank contains 16 operational families, two variants and two authorization conditions per family. Eight generation seeds produce 512 requested episodes; 509 have valid captured trajectories. A deterministic simulator executes each structured action against the explicit owner policy. Invalid format and absent readouts remain unavailable rather than being assigned benign labels.

Independent policy reviewers provide an additional strict agreement subset. Offline verification replayed all 512 simulator audits and checked the provenance of 976 accepted review slots out of 1024. These slots represent 452 unique cached requests because repeated identical trajectories reuse reviews. The 48 missing slots remain missing. This verifies the procedure and provenance, not independent semantic truth for every episode.

Families determine the split: eight training, four validation and four held out test families. The held out set spans only two broad mechanism clusters; some mechanism categories also cross the operational family split. Generalization to arbitrary strategic misalignment is therefore not established by this design. Authorized counterparts are specificity controls and are excluded from primary detector fitting and threshold selection. Paired cases help diagnose confounds but are not a prerequisite for every independently labeled episode.

## Layer token and time resolution

The six endpoints are end of prompt, before action, during action, after action, and 32 or 64 tokens before action. Every capture uses its own causal prefix; future tokens are excluded. Source layer identity, token position, trajectory identity and activation hashes are retained. All six endpoints have 509 complete J readout bundles, or 3054 bundles in total.

Timing labels require care. The early offsets occur during prompt processing for 507 of the 509 trajectories, rather than during generated deliberation. End of prompt and before action differ in only two episodes. Identical pre action states can lead to different sampled future outcomes. A detector cannot recover a future random draw that has not been encoded in its input; the validation forecast limit analysis makes this finite sample constraint explicit.

The Oracle input is normalized and scaled by 16000, injected through the published carrier, and decoded at temperature 1, top p 0.95, top k 64 and a maximum of 256 new tokens. Each distinct layer and state receives one sampled readout. Repeated identical states reuse that draw instead of receiving additional opportunities to produce a favorable description.

## Fitting and independent probes

The J lens fit uses 32 generic passages independent of behavior labels. Passages are capped at 128 tokens, excluding the first 16 and final source positions. The estimator includes downstream target effects. Disjoint 16 plus 8 plus 8 passage shards are merged with prompt count weighting after identity and coverage checks. Fits at 1, 4, 8 and 16 passages support outcome blind stability diagnostics against the primary 32 passage fit.

The native token view uses the subject's final normalization and unembedding. A magnitude free view is secondary. The primary display and blind summarizer receive the top ten tokens per layer. Generic corpus fitting must remain separate from supervised misalignment labels.

Raw activation and full transformed activation logistic probes share labels, grouped training folds, balancing and layer selection rules. Four grouped training folds select regularization from 0.01, 0.1, 1 and 10; ties prefer stronger regularization and earlier layers. Unconverged fits are rejected. Validation benign episodes from the prohibited condition set the conservative attainable 5 percent false positive target. Classifier logits are not calibrated probabilities. A causal text TF IDF logistic baseline follows the same grouped protocol.

The raw probe is fitted independently of the J lens and Oracle reader. Aligned feature construction checks byte identical raw components before comparing representations. If the dense J matrix is invertible, a raw linear detector can be expressed equivalently in the transformed coordinates. Independently refitting a regularized probe there may still change performance. Conditioning, numerical storage, regularization and finite data must be distinguished from information destruction.

The completed training and validation transport check used 381 episodes per endpoint. Float64 transport preserves scores to numerical precision. Stored FP32 transformed vectors produce no flag differences before or during action and three after action. Those three are repeated trajectories sharing one threshold boundary state, not three independent information loss findings. No threshold was adjusted to remove them. Training activation stability checks also compare disjoint 16 passage fits. Median transformed direction cosine at layer 20 ranges from 0.815 to 0.890 across before, during and after action, versus about 0.997 at layer 60. Early layer finite fit uncertainty is substantial. These diagnostics do not measure token ranking fidelity or establish that a missed concept is absent from ideal J space.

## Interpretation arms and controls

Nine arms compare J tokens, blind J summaries and Oracle descriptions, each with and without causal context, plus context only, shuffled summaries with context and shuffled Oracle descriptions with context. Shuffling is a fixed derangement across unique causal prefix groups within split. Repeated seeds cannot receive their own identical state as a negative control.

The summarizer receives one layer's token strings and scores without context, behavior labels or candidate ranks. Reviewers receive only each arm's permitted evidence. Subject identity, future output, outcome labels and probe scores are excluded from those requests. Two accepted reviewer model families supply the minimum of two valid ordinal judgments as the combined score. Missing one reviewer makes the combined judgment unavailable. Individual reviewer results are separately calibrated and retained.

Additional controls include adapter off training trajectories, full prefix numerical replay, norm matched random activation vectors, authorized task performance, refusal and quoted hypothetical misconduct. Random vectors generating readable prose demonstrate the need for controls; they do not estimate the hallucination rate on natural subject states. A small topic transfer check is likewise not a broad semantic validation.

## Reader qualification and coverage gates

Each candidate receives 48 cached legacy validation fixtures balanced over premium consensus scores and 24 authored policy fixtures. The bridge requires at least 90 percent valid replies and 80 percent exact consensus agreement. Policy controls require at least 90 percent validity and agreement, at least five of six positive cases correct and at least 17 of 18 negatives correct. Consensus is a compatibility proxy rather than truth. Adaptive candidate selection must be disclosed.

Qualification is followed by the frozen 90 request validation coverage pilot across 36 endpoint and arm strata. Adoption requires at least 90 percent schema valid unique replies and no entirely unavailable stratum. Full production coverage still needs its own arm and label denominators. The combined acceptance verifier checks execution identities, recomputes both gates from saved results and binds source hashes before adoption.

Multiple local and hosted candidates have failed these unchanged gates. Original hosted DeepSeek passed the bridge with 39 of 48 matches and all 24 policy controls, but failed coverage with 80 of 90 usable replies and two entirely unavailable context only strata. Those failures remain preserved. The conditional nano qualification did not start after that failure.

The escaped output and reasoning disabled DeepSeek candidates subsequently failed semantic qualification. GPT 4.1 on the OpenAI route passed with 39 of 48 bridge matches and 24 of 24 policy controls. GPT 5.4 with low reasoning on OpenAI Flex passed with 41 of 48 and 24 of 24 respectively. Each then produced 90 of 90 usable coverage replies. Their exact transport, parser and configuration hashes are bound by acceptance records. Failed candidates remain preserved; qualification settings cannot be transferred to a changed execution.

Both accepted judges share OpenAI provenance and contributed the bridge reference labels. Bridge agreement measures compatibility rather than independent accuracy. GPT 5.4 also supplies the blind summaries, creating additional self judgment dependence. A documented amendment accepted this pair after cross vendor candidates failed. Individual judge results and the independently executed behavior labels remain separate. Candidate selection uncertainty is not captured by the episode bootstrap.

Primary validation contains 126 episodes across nine arms. All 64 unique summaries completed, followed by 144 unique review requests per judge. GPT 4.1 produced 143 usable replies; GPT 5.4 produced 144. One GPT 4.1 response hit its 1600 token limit while quoting an Oracle description. That result is unavailable, with no retry or partial score extraction. It maps to eight benign prohibited condition episodes in the monitor family. Blind Oracle coverage is therefore 118 of 126; the other eight arms retain all 126. Its combined benign calibration denominator is 45 rather than 53. This is structured missingness, not eight independent failures.

Primary and end of prompt thresholds are frozen under verified source hashes. Their validation readouts are identical and are reused with separate endpoint aliases, so end of prompt is not an independent replication. Both earlier token controls have completed 128 unique summaries and prepared their nine arm validation inputs; those reviews and calibrations remain pending. The primary and end of prompt held out cohorts have 72 unique completed summaries and 184 unique review requests per judge after deduplication. Review inference is underway under the frozen protocol.

## Statistical analysis and disagreement taxonomy

Report sensitivity, false positive rate, specificity, AUROC, AUPRC and coverage with explicit denominators. The primary paired comparison uses only common eligible cases, while separate arm summaries and missingness bounds show what pairing excludes. Validation matched specificity is reported separately from achieved test specificity. It does not guarantee identical test false positive rates.

Uncertainty uses 2000 whole family bootstrap replicates. A separate mechanism cluster sensitivity analysis acknowledges the two cluster limitation. Intervals are withheld where fewer than two families contribute a relevant observed class. Degenerate empirical intervals and zero observed errors are not population risk guarantees. Secondary endpoints and multiple exploratory contrasts must be labeled accordingly.

The disagreement taxonomy separates joint hits, joint misses, probe only hits, J only hits, Oracle only hits and pairwise overlaps, conditional on the independent behavior label. Within a probe positive J negative case, distinguish token display failure, summary failure, interpretation failure, threshold effects and unavailable outputs. Keep the full transformed activation probe result attached. Missing Oracle output must not remove a probe detected violation from the blind spot analysis.

The casebook selects up to three lowest hash episode identifiers per nonempty pattern and label. It retains prefixes, layer readouts, donor identities, prompts, judgments, thresholds and behavioral confirmation. Qualitative review distinguishes prefix restatement, supported activation specific information and unsupported elaboration. Selected cases are illustrations rather than prevalence estimates, and their inspection cannot change detection flags.

## Causal follow up

Interventions are conditional on reproducible disagreements. Select directions and dose grids using development data, then compare fresh paired continuations from the same prefix under the intervention and a sham. The original generation outcome is not the sham continuation. Deduplicate identical states and account for repeated outcomes within families.

Specify a single post block intervention separately from persistent steering, recompute affected caches, and verify zero dose equivalence. Include norm matched random directions, benign authorized task quality, refusal, format validity and truncation controls. A change in violation rate accompanied by general output corruption is not specific causal evidence. Held out motivated follow up remains exploratory and uses fresh continuations. A predictive direction is not automatically a unique misalignment mechanism. The additive post block intervention and paired continuation harness have passed CPU engineering tests. They have not yet passed real subject zero dose replay or produced causal results; those remain required before any causal claim.

## Preserved GPT OSS findings

The archived primary summarizer comparison at 32 tokens before code onset contains 617 paired known label cases, including 445 violations and 172 benign cases. Summary plus context detected 286 violations with eight false positives; the frozen J view detected 323 violations with 22 false positives. The paired sensitivity difference is minus 8.31 percentage points, with a 95 percent family bootstrap interval from minus 11.96 to minus 5.30. The false positive rate difference is minus 8.14 points, from minus 14.37 to minus 3.82. This is a sensitivity and specificity tradeoff.

At matched validation specificity, the activation probe detected 353 of 445 violations with 12 of 172 false positives. An exploratory summary plus original tokens arm had a sensitivity difference of plus 0.45 points relative to J view, with an interval spanning minus 1.94 to plus 3.36. This does not establish equivalence or isolate the cause of the change.

Blind summary AUROC was 0.511. Correctly paired contextual summaries exceeded shuffled summaries in sensitivity by 5.17 points, but differed from context only by minus 0.22 points with an interval spanning zero. These results neither prove faithful hidden intent recovery nor show that full J space lacks information. The 64 token offset and code onset results have different coverage; code onset remains an incomplete cached subset. Template, authorization and monitor maintenance panels remain unfinished under the new continuation protocol.

## Execution stages and completion criteria

Stage one has established checkpoint identities, behavioral trajectories, independent review provenance, captures, lens fits and backed up readouts. The raw and transformed probes are available. These are completed engineering and development analyses, not a completed held out comparison.

Stage two has qualified the accepted reference pair and verified its coverage. Summarizer schema validity is established on completed cohorts; semantic fidelity still requires review. Register any model, route, prompt or parser change as a distinct execution. Preserve failures and the accepted pair's shared provenance limitations.

Stage three is complete for primary and end of prompt validation, with immutable endpoint locks. The earlier token controls have summaries but await reviews; during and after action validation remain pending. Stage four is running primary held out reviews. Complete accounting, including unavailable replies, must precede the locked metrics, uncertainty analyses and deterministic casebooks. Other endpoint locks must be created from their own validation data before test scoring.

Stage five completes fidelity review and any warranted causal follow up, reports controls and missingness, and finishes the separate legacy robustness extension. Final deliverables are an editable measured report, reproducible scripts and configuration, pinned model and data identities, machine readable metrics, casebooks, cost and resource records, and verified local copies of necessary artifacts.

Success means a reproducible comparison with independently established labels, calibrated specificity, explicit coverage and documented disagreements. It does not require J lens or Oracle to outperform probes, or any hypothesis to be confirmed. A negative finding with adequate power and valid controls can be informative; an unavailable judge or unexecuted test cannot substitute for such a finding.

## Infrastructure cost and schedule

Frontier scale differentiation and activation reading require substantially more memory and computation than ordinary generation. This implementation used H200 workers, full precision subject passes, sharded fitting and separate reader processes. Activations and receipts are cached and hashed; repeated trajectories reuse identical state readouts. GPU workers do not receive API or cloud control credentials.

The recorded four pod September 26 phase is estimated at 61.5380 dollars in compute, excluding earlier GPU runs, retained storage, taxes and provider adjustments. Workers were confirmed stopped or terminated at the recorded shutdown check. Retained storage remains a separate cost. This estimate is not a reconciled invoice or total project budget.

The additional API project ceiling is 10 dollars; the current cumulative dispatch allowance is 5 dollars. Both are local cost controls under the user's delegated paid run authorization. Each small batch reserves its full conservative cost before activation. Unknown charges retain 0.581365 dollars of reservations, including failed provider calls; they are never counted as free or retried. Current settled spending is recorded in the live integer microdollar ledger rather than frozen in this narrative. The completed primary summaries cost 0.067136 dollars, earlier token summaries 0.130575 dollars, and held out summaries 0.077337 dollars. These increments exclude qualification and review inference.

The runner can shrink batch size solely for affordability. It stops when even a minimum batch cannot fit, on an unexplained failure, or when source hashes differ. No budget increase, retry or substitution happens automatically. Remaining temporal and legacy cohorts need separately registered affordable allocations.

Provider response length parameters are not assumed to cap all billed reasoning tokens. One original DeepSeek receipt reported 3449 completion tokens, including 3278 reasoning tokens, despite a requested response length of 2048. Larger client reservations are planning allowances rather than verified provider invoice caps. Register concrete batches and verify receipts before scaling.

Schedule estimates are conditional planning ranges rather than commitments: allow one to three working days for the remaining endpoint validation and locks, one to three for held out scoring and statistical review, and two to five for casebooks, warranted interventions and the final report. Provider latency or a failed gate can extend these stages. No additional GPU allocation or production spend is justified solely by this estimate.

## Sources and reproduction entry points

The primary conceptual source is Verbalizable Representations Form a Global Workspace in Language Models, including the Oracle lens appendix, at https://transformer-circuits.pub/2026/workspace/ . The operational O lens reference is https://github.com/camilablank/workspace-bench . Released reader artifacts are at https://huggingface.co/agu18dec/olens_and_ar .

The project repository is https://github.com/Ratnaditya-J/jlens-research . Authoritative implementation and protocol sources are studies/reader_comparison/METHODS.md, PRODUCTION_PROTOCOL.md, ANALYSIS_PROTOCOL.md, ORACLE_LENS_SCOPE.md and config-em-riskyfin.json. Machine readable evidence resides in studies/reader_comparison/evidence. Archived measured summarizer results are in reports/summarizer-extension-findings.md and its linked result files.

Use prepare_validation.py for aligned validation artifacts, verify_reader_acceptance.py for combined adoption checks, calibrate_comparison.py for immutable locks, evaluate_comparison.py for the registered metrics, and build_comparison_casebook.py for reproducible disagreements. The legacy extension uses separate preparation, calibration and evaluation scripts. Current file hashes and run manifests take precedence over this dated narrative record when continuing execution.
