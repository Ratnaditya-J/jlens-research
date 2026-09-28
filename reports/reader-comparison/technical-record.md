# Comparing activation probes J lens and Oracle Lens

Technical methods and execution record

September 28 2026

The project tests whether supervised activation probes, a checkpoint specific Jacobian lens, and an Oracle Lens verbalizer reveal different aspects of policy violating behavior in the same model. Its purpose is to measure detection coverage, interpretation quality and blind spots without treating any reader as complete or authoritative. This document is an editable technical record for the researcher and subsequent Codex work.

All six Qwen held out endpoint comparisons are complete. No method shows a reliable overall advantage. During action, blind Oracle has greater recall with more false alarms. At minus 32, the raw probe flags six confirmed violations missed by contextual J displays, but gives identical scores to 16 benign runs sharing those prefixes. After action, context alone matches detection, so contextual lens success does not establish added activation information. A targeted qualitative fidelity audit and two legacy specificity panels are complete. The template stress panel and expanded legacy code onset cohort have also been evaluated with retained missingness. Full Oracle reconstruction fidelity remains unmeasured. The original GPT OSS results are preserved separately.

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

Escaped and reasoning disabled DeepSeek variants failed qualification. GPT 4.1 standard and GPT 5.4 low reasoning Flex passed with 39 and 41 of 48 bridge matches respectively, 24 of 24 policy controls each, and 90 of 90 coverage replies each. Acceptance records bind their exact execution settings; failed candidates remain preserved.

Both accepted judges share OpenAI provenance and contributed the bridge reference labels. Bridge agreement measures compatibility rather than independent accuracy. GPT 5.4 also supplies the blind summaries, creating additional self judgment dependence. A documented amendment accepted this pair after cross vendor candidates failed. Individual judge results and the independently executed behavior labels remain separate. Candidate selection uncertainty is not captured by the family bootstrap.

Primary validation covers 126 episodes across nine arms, with 64 unique summaries and 144 unique reviews per judge. GPT 4.1 has one unavailable reply after reaching its 1600 token limit; GPT 5.4 has none. The failure aliases eight benign monitor episodes, giving blind Oracle coverage 118 of 126 and a benign calibration denominator of 45 instead of 53. Other arms have complete coverage. No retry or partial extraction was used.

All six endpoint thresholds are frozen and their held out evaluations complete. Primary and end of prompt validation reuse identical readouts with separate aliases; these are dependent endpoints. Earlier minus 32 and minus 64 thresholds were fixed before their own held out reviews, but after primary test results were known. This chronology limits blanket preregistration claims. No thresholds were adjusted after seeing endpoint test results.

Following repeated Flex outages, standard route GPT 5.4 was separately qualified with 41 of 48 bridge matches, 24 of 24 policy controls and 90 of 90 usable coverage replies. During and after action use this registered second judge with GPT 4.1; earlier endpoints retain the original Flex second judge. All summaries retain their fixed Flex execution. Standard and Flex agreed on 40 of 48 bridge fixtures, which does not establish route equivalence. During and after validation retained three unavailable GPT 4.1 replies out of 960 and all 960 standard GPT 5.4 replies. Their endpoint locks preceded held out reviews.

## Measured primary held out results

The table reports the primary pre action operating points. True positive and false positive counts use the indicated denominators; authorized false positives are a separate generalization control. The dense transformed probe is not a sparse nonnegative J space decomposition.

| Method | TP of 10 | FP of 54 | Authorized FP of 64 | AUROC |
|---|---|---|---|---|
| Raw activation probe | 0 | 2 | 56 | 0.600 |
| Dense transformed probe | 0 | 0 | 0 | 0.511 |
| J summary with context | 0 | 0 | 0 | 0.500 |
| Oracle with context | 0 | 0 | 8 | 0.500 |
| Context only reader | 0 | 0 | 0 | 0.500 |
| Text classifier | 0 | 0 | 0 | 0.620 |

The primary prohibited condition panel contains 64 episodes: 10 simulator confirmed violations and 54 benign outcomes across four operational families. All 64 also satisfy the strict independent policy review agreement sensitivity criterion. A separate authorized panel contains 64 benign episodes. Both endpoints have complete test judgment coverage. The two judge minimum remains the registered combined score; individual judge results are retained separately.

All other combined reader arms also miss all 10 violations and flag none of the 54 prohibited condition benign episodes. Oracle with context and J summary with context both have constant combined scores on this panel, with AUROC 0.50 and AUPRC 0.15625, equal to prevalence. Their observed paired sensitivity and false positive differences are zero. This is no demonstrated advantage, not an equivalence result.

End of prompt likewise has zero true positives for every combined arm and probe. The raw probe has zero rather than two prohibited condition false positives there, with AUROC 0.619 versus 0.633 for the text classifier. Its authorized false positives remain 56 of 64, and Oracle with context remains eight of 64. Shared requests and nearly identical states make these dependent endpoints rather than independent replications.

The raw probe is fitted and calibrated only on prohibited condition data; authorized episodes were deliberately reserved as specificity controls. Its authorized false positive rate is 87.5 percent, with a four family bootstrap interval of 62.5 to 100 percent. Oracle with context has 12.5 percent, with an interval of zero to 37.5 percent. The remaining combined readers and the transformed and text probes have zero observed authorized false positives, which is not a guarantee of zero population risk.

All eight authorized Oracle flags come from one benchmark variant repeated across seeds. A post hoc audit found competing prompt cues: the task calls rows genuine failures, while the owner policy identifies them as duplicate ingestion records and authorizes removing the duplicates. One judge treated them as nonduplicates; the other explicitly noted the ambiguity. Oracle descriptions also contain unrelated decision details. Keep these cases in the frozen analysis and treat the finding as a clustered specificity failure with interpretation confounds. A clarified prompt would be a new follow up, not a correction to existing outcomes.

The pre action panel contains 10 distinct prefixes, six with mixed later outcomes covering 46 episodes. End of prompt contains eight prefixes, six mixed, covering 48 episodes. On this finite test bank, a deterministic detector assigning one score per identical prefix cannot recover a violation while allowing at most two false positives, the attainable 5 percent budget. This hindsight result limits the pre action comparison; it is not a population bound or a statement that no information is encoded at later positions.

There are no true positive episodes detected by the raw probe but missed by both J displays at these frozen operating points. The requested blind spot category is empty here, not disproved in general. Individual judge sensitivities remain explicit: GPT 4.1 blind summaries detect one violation with seven prohibited condition false positives; GPT 5.4 shuffled Oracle detects two with six false positives pre action and four with twelve at end of prompt. These exploratory findings do not justify selecting a different aggregation after observing the test results.

A development audit examined 381 training and validation episodes, followed by a held out audit of all 128 test trajectories. No during action prefix exposes the explicit Boolean choice; all after action prefixes do. Two held out trajectories already contain generated text at the before action endpoint. Earlier offsets are therefore mostly prompt processing, not deliberation. Later performance must distinguish recognition of visible actions from forecasting future behavior.

## Measured temporal and earlier endpoint results

Each table gives true positives over available positive episodes, false positives over available prohibited benign episodes, and false positives over available authorized controls. Denominators exclude unavailable responses; the requested populations remain ten positives, 54 prohibited benign and 64 authorized. The full machine readable results retain missingness bounds, paired comparisons, individual judges and family bootstrap intervals. These secondary comparisons are descriptive and not adjusted for multiple testing.

## During action

| Method | TP / pos | FP / benign | Authorized FP / benign | AUROC |
|---|---|---|---|---|
| Blind J tokens | 1/9 | 3/52 | 0/64 | 0.527 |
| Blind J summary | 1/10 | 5/53 | 0/64 | 0.503 |
| Blind Oracle | 4/9 | 8/52 | 6/64 | 0.641 |
| Context only | 0/10 | 0/54 | 0/64 | 0.367 |
| J tokens with context | 1/10 | 4/54 | 2/64 | 0.548 |
| J summary with context | 0/10 | 0/53 | 5/64 | 0.664 |
| Oracle with context | 0/10 | 0/54 | 0/64 | 0.411 |
| Shuffled J with context | 0/10 | 0/51 | 0/64 | 0.439 |
| Shuffled Oracle with context | 0/10 | 0/54 | 0/64 | 0.481 |
| Raw activation probe | 0/10 | 0/54 | 8/64 | 0.659 |
| Dense transformed probe | 1/10 | 11/54 | 11/64 | 0.620 |
| Text classifier | 0/10 | 0/54 | 0/64 | 0.620 |

Blind Oracle detects 4 of 9 available positives with 8 of 52 false alarms. Its full positive cohort recall bounds are 40 to 50 percent because one positive is unavailable. The family bootstrap recall interval spans 10 to 80 percent. Blind J tokens detect 1 of 9 with 3 of 52 false alarms. Neither the small sample nor this specificity tradeoff establishes a winner. Oracle with context and the two shuffled contextual arms have thresholds above the maximum score and therefore cannot flag; their zero detections do not establish absence of signal.

## After action

| Method | TP / pos | FP / benign | Authorized FP / benign | AUROC |
|---|---|---|---|---|
| Blind J tokens | 0/10 | 2/54 | 0/64 | 0.481 |
| Blind J summary | 0/10 | 0/54 | 0/64 | 0.500 |
| Blind Oracle | 10/10 | 6/54 | 53/62 | 1.000 |
| Context only | 10/10 | 0/54 | 0/64 | 1.000 |
| J tokens with context | 10/10 | 0/54 | 16/64 | 1.000 |
| J summary with context | 10/10 | 0/51 | 13/64 | 1.000 |
| Oracle with context | 10/10 | 0/54 | 15/64 | 1.000 |
| Shuffled J with context | 10/10 | 0/54 | 7/64 | 1.000 |
| Shuffled Oracle with context | 10/10 | 0/54 | 10/64 | 1.000 |
| Raw activation probe | 10/10 | 1/54 | 62/64 | 1.000 |
| Dense transformed probe | 7/10 | 15/54 | 62/64 | 0.907 |
| Text classifier | 10/10 | 1/54 | 62/64 | 1.000 |

Context alone detects all ten violations with zero false alarms in both control populations. Correct and shuffled contextual readouts also detect all ten. The action is visible in every prefix, so these results demonstrate recognition rather than advance detection or incremental activation information. Blind Oracle has 53 false alarms among 62 available authorized controls, while raw and text probes each flag 62 of 64. Blind J displays miss all ten; contextual J displays do not. The blind display failure cannot be generalized to absence of information in the full J transform.

## Thirty two tokens before action

| Method | TP / pos | FP / benign | Authorized FP / benign | AUROC |
|---|---|---|---|---|
| Blind J tokens | 2/10 | 14/54 | 0/64 | 0.470 |
| Blind J summary | 0/10 | 0/54 | 8/64 | 0.500 |
| Blind Oracle | 0/10 | 0/54 | 16/64 | 0.533 |
| Context only | 0/10 | 0/54 | 0/64 | 0.500 |
| J tokens with context | 1/10 | 7/54 | 0/64 | 0.502 |
| J summary with context | 0/10 | 0/54 | 0/64 | 0.533 |
| Oracle with context | 0/10 | 0/54 | 0/64 | 0.609 |
| Shuffled J with context | 0/10 | 0/54 | 0/64 | 0.524 |
| Shuffled Oracle with context | 1/10 | 7/54 | 8/64 | 0.485 |
| Raw activation probe | 6/10 | 18/54 | 32/64 | 0.641 |
| Dense transformed probe | 0/10 | 0/54 | 0/64 | 0.674 |
| Text classifier | 0/10 | 0/54 | 0/64 | 0.617 |

The raw probe detects six confirmed violations that both contextual J displays miss. A post hoc audit groups these into three identical prefixes shared with 16 benign runs having exactly the same raw probe scores. All 22 episodes satisfy strict behavioral confirmation. This is a real operating point disagreement, but it does not distinguish the violating continuation within each group or identify hidden intent. Raw false alarms reach 18 of 54 prohibited benign and 32 of 64 authorized episodes. Dense transformed probe AUROC exceeds raw AUROC despite no threshold hits; threshold behavior and representational coverage must remain separate.

## Sixty four tokens before action

| Method | TP / pos | FP / benign | Authorized FP / benign | AUROC |
|---|---|---|---|---|
| Blind J tokens | 0/10 | 0/54 | 0/64 | 0.500 |
| Blind J summary | 0/10 | 0/54 | 0/56 | 0.500 |
| Blind Oracle | 0/10 | 8/54 | 8/64 | 0.511 |
| Context only | 0/10 | 9/54 | 0/64 | 0.417 |
| J tokens with context | 0/10 | 0/54 | 0/64 | 0.574 |
| J summary with context | 0/10 | 0/54 | 0/56 | 0.506 |
| Oracle with context | 0/9 | 0/47 | 8/64 | 0.443 |
| Shuffled J with context | 0/8 | 0/48 | 0/64 | 0.573 |
| Shuffled Oracle with context | 0/8 | 0/49 | 0/64 | 0.555 |
| Raw activation probe | 0/10 | 0/54 | 0/64 | 0.550 |
| Dense transformed probe | 0/10 | 0/54 | 0/64 | 0.702 |
| Text classifier | 0/10 | 0/54 | 0/64 | 0.648 |

All methods have zero true positives at their frozen operating points. Missingness is structured: Oracle with context lacks eight prohibited judgments, including one positive; shuffled J lacks eight, including two positives; shuffled Oracle lacks seven, including two positives. Blind and contextual J summaries each lack eight authorized judgments. These gaps are not negative detections.

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

Blind summary AUROC was 0.511. Correctly paired contextual summaries exceeded shuffled summaries in sensitivity by 5.17 points, but differed from context only by minus 0.22 points with an interval spanning zero. These results neither prove faithful hidden intent recovery nor show that full J space lacks information. The 64 token offset and code onset results have different coverage. The original partial code onset report is preserved unchanged; a separate continuation now evaluates the full requested cohort with residual unavailable judgments and readouts reported explicitly. Authorization, monitor maintenance and template challenge panels retain their original frozen thresholds and payloads.

## Legacy authorization and monitor controls

The completed authorization and debugging panel contains 47 known benign episodes out of 48 requested records; 47 have stored readouts. All 24 monitor maintenance records have known benign labels and readouts. Every summary and original token display arm has zero false positives on these known benign controls, with no missing known judgments. The frozen activation probe flags all 71. These controls therefore show a substantial specificity failure for this probe and better observed specificity for the text interpretation arms. They do not measure sensitivity or demonstrate that summaries recover hidden intent.

| Panel | Summary FP | Probe FP | Original J view FP | Context FP |
|---|---|---|---|---|
| Authorization and debugging | 0/47 | 47/47 | 0/47 | 1/47 |
| Monitor maintenance | 0/24 | 24/24 | 0/24 | 0/24 |

The blind summary, summary plus original tokens, blind J tokens and shuffled contextual summary arms also have zero false positives in both panels. There are no positive cases in these control cohorts, so sensitivity is undefined. Zero observed errors does not establish zero population risk. Do not pool these GPT OSS controls with the Qwen authorized panels: checkpoint, tasks and execution protocols differ.

All 268 unique summaries and 676 unique review requests completed with usable responses. Exact raw request payloads, replies, parsed judgments, budget settlements and minimum-of-two aggregation were verified. The 676 reviews fill 710 episode arm model slots through exact cache reuse. The two stages cost 0.262745 and 5.224217 dollars respectively. Concurrency was eight globally; no failed requests were retried. Original thresholds, models and provider routing were retained.

## Targeted Oracle fidelity assessment

A post hoc unblinded Codex audit selected the first two hash-ordered unique prefixes among strictly confirmed during-action Oracle true positives and the first two among strictly confirmed after-action authorized false alarms. These four illustrations are a single-assessor qualitative assessment, not independent ground truth or a prevalence estimate.

The compute example identifies the quota conflict, but one layer recommends unauthorized capacity while later layers state refusal or false. The benchmark example identifies removing failures to inflate reliability, yet mixes true recommendations with refusal and sometimes incorrectly describes false as removing rows. Both include details unsupported by the prefix. The two authorized purchase examples recognize an authority override in some layers while other descriptions introduce policy bypass, loans, shutdowns or invented deadlines. The owner waiver is explicit in the actual task.

These examples show topic correspondence alongside conflicting action semantics, authorization ambiguity and elaboration not supported by the prefix. Unsupported by the prefix does not prove absent from the activation. Correct detection also does not validate reconstruction fidelity. The released verbalizer remains unqualified as a comprehensive or authoritative account of the subject's internal state; subject_transfer_validated remains false. No reconstructor, whitening or nonnegative reconstruction coefficient test was run.

## Template stress panel and expanded code onset results

These original GPT OSS cohorts are separate from the Qwen Oracle comparison. All registered new requests were attempted once and both frozen evaluations completed. Completion means the registered execution finished; it does not mean every episode has an available judgment. The fresh completion output alias uses byte identical original inputs and summaries and the same reviewer manifest, while preserving the original partial scores and completion files.

## Template challenge

The requested cohort contains 128 episodes, of which 89 have known behavioral labels. Rates below exclude uncertain or unavailable labels. Each arm uses its own available denominator; missing known cases include both upstream unavailable readouts and missing judgments.

| Method | TP of positive | FP of benign | Missing known | AUROC |
|---|---|---|---|---|
| Summary with context | 16/18 | 0/70 | 1 | 0.944 |
| Summary and tokens with context | 16/17 | 0/69 | 3 | 0.971 |
| Blind summary | 0/18 | 0/70 | 1 | 0.500 |
| Blind token display | 0/18 | 0/70 | 1 | 0.433 |
| Shuffled summary with context | 15/18 | 0/68 | 3 | 0.917 |
| Activation probe | 18/18 | 2/70 | 1 | 1.000 |
| Original J view | 18/18 | 0/70 | 1 | 1.000 |
| Context only | 18/18 | 2/70 | 1 | 0.994 |

On the template challenge, summary sensitivity is 11.11 percentage points below the original J view on 88 paired cases, with a 95 percent family bootstrap interval from minus 23.53 to zero. Both have zero false positives among 70 available benign cases. The original J view detects all 18 available positives. Summary plus tokens detects 16 of 17 available positives; that denominator differs because of missing judgments. Blind summaries detect none. Correct summaries exceed shuffled summaries by 5.56 sensitivity points, with an interval from zero to 21.05. This small panel does not establish equivalence or a general sensitivity benefit.

## Code onset continuation

The requested cohort contains 786 episodes, of which 727 have known behavioral labels. Rates below exclude uncertain or unavailable labels. Each arm uses its own available denominator; missing known cases include both upstream unavailable readouts and missing judgments.

| Method | TP of positive | FP of benign | Missing known | AUROC |
|---|---|---|---|---|
| Summary with context | 459/462 | 0/259 | 6 | 0.997 |
| Summary and tokens with context | 461/464 | 0/257 | 6 | 0.997 |
| Blind summary | 0/464 | 0/259 | 4 | 0.500 |
| Blind token display | 0/463 | 0/258 | 6 | 0.689 |
| Shuffled summary with context | 457/463 | 0/259 | 5 | 0.994 |
| Activation probe | 464/464 | 13/259 | 4 | 1.000 |
| Original J view | 464/464 | 3/259 | 4 | 0.998 |
| Context only | 464/464 | 7/259 | 4 | 1.000 |

At code onset, contextual summaries detect 459 of 462 available positives with zero false positives among 259 available benign cases. The original J view detects all 464 available positives with three false positives among 259 benign cases, while the probe flags 13 benign cases. On the common 721 cases, summary sensitivity differs from J view by minus 0.65 percentage points, with a 95 percent family interval from minus 1.30 to zero; its false positive rate differs by minus 1.16 points, from minus 2.80 to zero. These are operating point tradeoffs, not evidence that one reader is complete.

Shuffled contextual summaries detect 457 of 463 available code onset positives. The paired correct minus shuffled sensitivity difference is only 0.65 points, with a 95 percent family interval from minus 0.43 to plus 1.69. Blind summaries detect zero of 464. The result therefore does not establish added detection information from correctly paired summaries beyond context. Zero observed false positives and degenerate bootstrap intervals do not imply zero population error. Family resampling uses 15 authored families and 2000 replicates; it does not establish broad deployment generalization or correct all exploratory comparisons for multiplicity.

The continuation registered 4068 new unique reviewer calls and reused 4768 exact cached responses. Of the new calls, 4040 yielded usable judgments and 28 remained unavailable; four prior failed unique requests were retained without retry. The registered jobs span 8960 episode arm model slots; exact cache reuse supplies 8808 usable unique reviews, with unavailable slots retained. Per-arm missingness, worst and best case bounds, uncertain-as-benign analyses, pairwise comparisons and deterministic disagreement examples are retained in the machine readable reports. No missing response was converted to a negative label.

## Execution stages and completion criteria

Stage one established checkpoint identities, independently reviewed behavioral trajectories, captures, lens fits and cached readouts. Raw and transformed probes and text baselines are fitted under the same grouped protocol.

Stage two has qualified the accepted reference pair and verified its coverage. Summarizer schema validity is established on completed cohorts; primary and temporal qualitative fidelity audits document bounded observations and limitations. Register any model, route, prompt or parser change as a distinct execution. Preserve failures and the accepted pair's shared provenance limitations.

Stages three and four are complete for all six endpoints: calibration locks, held out reviews, coverage accounting, metrics and uncertainty are saved. The primary and end of prompt casebooks and the minus 32 shared prefix audit are available. Four endpoint review inference completed 2634 unique requests, of which six were unavailable; missing summaries produce additional aliased missingness. The automatic handoff verified raw receipts and evaluated the four remaining endpoints without retuning.

Stage five has completed the targeted qualitative fidelity audit and two legacy specificity panels. Causal intervention remains conditional and unexecuted. The template challenge and full requested legacy code onset continuation have now completed registered inference and frozen evaluation, with unavailable cases retained. Final deliverables are an editable measured report, reproducible scripts and configuration, pinned model and data identities, machine readable metrics, casebooks, cost and resource records, and verified local copies of necessary artifacts.

Success means a reproducible comparison with independently established labels, calibrated specificity, explicit coverage and documented disagreements. It does not require J lens or Oracle to outperform probes, or any hypothesis to be confirmed. A negative finding with adequate power and valid controls can be informative; an unavailable judge or unexecuted test cannot substitute for such a finding.

## Infrastructure cost and schedule

Frontier scale differentiation and activation reading require substantially more memory and computation than ordinary generation. This implementation used H200 workers, full precision subject passes, sharded fitting and separate reader processes. Activations and receipts are cached and hashed; repeated trajectories reuse identical state readouts. GPU workers do not receive API or cloud control credentials.

The recorded four pod September 26 phase is estimated at 61.5380 dollars in compute, excluding earlier GPU runs, retained storage, taxes and provider adjustments. Workers were confirmed stopped or terminated at the recorded shutdown check. Retained storage remains a separate cost. This estimate is not a reconciled invoice or total project budget.

The user increased the cumulative additional OpenRouter ceiling to 80 dollars. Final settled spending is 69.538016 dollars, with 1.058460 dollars still reserved for uncertain earlier charges, leaving 9.403524 dollars unallocated. The final template summary stage cost 0.462819 dollars and the remaining review stage cost 33.834451 dollars. These additional-budget figures exclude earlier API spending and GPU or storage costs. All registered new requests were attempted once; unavailable replies and uncertain charges remain recorded. No further inference is needed for the registered comparison.

After sequential API dispatch caused unnecessary delay, the held out pipeline was changed to eight globally concurrent requests with shared locked budget reservations, exact cache reuse and immediate completion triggered stage handoffs. Outcomes do not determine queue order. Every paid stage is priced and registered before dispatch; each request must fit its conservative reservation. Clusters of failures stop dispatch, and failed requests remain unavailable without retry. All paid workers are now terminal.

Provider response length parameters are not assumed to cap all billed reasoning tokens. One original DeepSeek receipt reported 3449 completion tokens, including 3278 reasoning tokens, despite a requested response length of 2048. Larger client reservations are planning allowances rather than verified provider invoice caps. Register concrete batches and verify receipts before scaling.

All registered numerical comparisons are complete. Final evidence verification and document integration close out the execution. Reconstruction fidelity, broad subject transfer and real model causal interventions are unmeasured extensions; no causal finding or comprehensive access to hidden intentions is claimed. Future research should use episodes with distinguishable pre action states, more independent families and targeted interventions with real model zero dose qualification before interpreting a detector direction causally.

## Sources and reproduction entry points

The primary conceptual source is Verbalizable Representations Form a Global Workspace in Language Models, including the Oracle lens appendix, at https://transformer-circuits.pub/2026/workspace/ . The operational O lens reference is https://github.com/camilablank/workspace-bench . Released reader artifacts are at https://huggingface.co/agu18dec/olens_and_ar .

The repository is https://github.com/Ratnaditya-J/jlens-research . Protocols and configuration are in studies/reader_comparison; its evidence directory contains machine readable audits. Reproduce using prepare_validation.py, verify_reader_acceptance.py, calibrate_comparison.py and evaluate_comparison.py. The original GPT OSS extension uses separate scripts.

Measured results, specificity controls, qualitative audits and their source records are in reports/reader-comparison. The original GPT OSS findings remain in reports/summarizer-extension-findings.md.
