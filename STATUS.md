# J-lens and probe comparison status

Persistent task `j-lens-and-probe-research` runs every 10 minutes. User authorizes autonomous decisions and paid APIs/RunPod; account balances auto-replenish. Respect configs/resources.json. No routine permission questions. Never fabricate a definitive comparison.

User-required final deliverable: four-way paired held-out counts (probe only, J-lens only, both, neither), percentages, denominator, and case-level CSV. Break down by independently confirmed misaligned/benign labels; disclose missing scores/abstentions separately. Full contract is in reports/method-decisions.md under Required final four-way detection breakdown.

## Current execution

H200 pod `dzxjkojt1pbuip` provisioned for FP32 identity validation and 99-episode developmental confirmation. Rate $4.59/hour. Six-hour watchdog runs in exec session 83617; deadline in runs/pod.json. SSH endpoint in that file; private key ../../work/private/pod_ed25519, known_hosts alongside it. Workload transferred and launched. SSH 31.24.80.26 port 19124. Hardware verified: NVIDIA H200, 143771 MiB.

Workload: scripts/bootstrap_confirmation.sh installs pinned packages, runs gpu_identity.py with IDENTITY_CONFIG=configs/identity-fp32.json and IDENTITY_OUTPUT=runs/identity-fp32, then behavior_pilot.py with BEHAVIOR_CONFIG=configs/behavior-confirmation.json and BEHAVIOR_OUTPUT=runs/confirmation. Identity timeout one hour, behavior timeout four hours. No other GPU jobs should overlap. Credentials remain local; guest model code is never run on GPU host.

## Completed evidence

- Pinned adapter `9e11602b9e67211887229ed20d0ac79e412ee910`, BF16 base `cc89b3e7fd423253264883a80a4fa5abc619649f`, J-lens reference `581d398613e5602a5af361e1c34d3a92ea82ba8e`, AISI reference `169c3c76a02e51092b4023a8c7baba38f41e2800`. Metadata and source paths in manifests/.
- BF16 pilot: all 192 LoRA tensors loaded; adapter changes logits, no-op hook and manual unembedding parity exactly zero. Peak CUDA allocation about 45 GB. Cached replay error max 2.375 means replay parity is not established. Live uncached activation capture used instead.
- BF16 derivatives were unstable. FP32 isolated last-block diagnostic achieved 0.2% relative finite-difference error with stable expert routes. This does not validate a full BF16 lens. Full FP32 execution now being tested; it is a separate precision identity requiring behavior reconfirmation.
- Nine BF16 episodes collected, all activation hashes verified. Primary evaluation-interference counts: 4 clear violations, 1 benign, 4 uncertain/unavailable. Broad API labels for hardcoded examples were conservatively not accepted as confirmed interference. Full evidence in runs/behavior/pilot-summary.json. Original A100 pod cvwo3adm7a2a20 terminated after collection; archived manifest in runs/pod-cvwo3adm7a2a20.json.
- WASI execution sandbox implemented, five containment/runtime tests passed. Wasmtime 48.0.0 local venv ../../work/wasm-venv, SHA-verified Python 3.12.0 WASI runtime ../../work/wasm-runtime. Read-only /usr and /work, no inherited environment or sockets, 512MB/fuel/time/output caps. Use this for generated code; macOS sandbox-exec and RunPod namespaces were unavailable.
- scripts/audit_episode.py handles single Python-block string-return tasks. Other formats and multi-file pytest cases remain explicit unavailable until source parser compatibility is implemented.
- scripts/adjudicate_episode.py invokes separate GPT-4.1 and GPT-5.4 reviewer calls, blind to internal scores and each other. Rubric v2 distinguishes forbidden hack hints from authorization. Preserve v1 disagreement and all revised requests. Same-provider reviewers may correlate; no human-readability claim.

## Next actions

1. Check FP32 identity progress and report; collect outputs. Do not claim lens validity merely because finite gradients exist. Evaluate finite differences, routes and replay.
2. Collect completed runs/confirmation episode directories, verify activation hashes, and execute WASI audits locally, then blinded API adjudication. Keep FP32 and BF16 labels separate. All current episodes are DEVELOPMENT data.
3. Reach 30 confirmed positive and 30 benign episodes across three templates in the chosen precision. The expanded corpus adds simple arithmetic, sequences and strings under the same source_dont_hack/fresh_strict/fresh_no_hints conditions. Assess topic and difficulty confounds; do not use test data to improve yield.
4. Fit the genuine pinned J-lens estimator on disjoint generic data only after numeric validity; generic reference tiny tests and convergence checks are still required. No J-lens has been fitted yet.
5. Train grouped logistic regression, freeze the independent J-view rubric and 5% FPR validation threshold, then evaluate paired coverage, specificity, timing and disagreements on locked held-out data. Full pipeline CLI and probe/evaluation modules remain to implement.
6. Stop idle project GPU jobs after collecting and verifying results; terminate when no immediate use remains. Update resource ledger and this status at each stage. Report milestones here once, not routine polls.

## Reported milestones

First nine-episode behavioral pilot completed; first externally verified independently reviewed unauthorized reward-hacking behavior reported. About 10% overall completion. 30/30 behavior gate NOT passed; fitted lens, trained probe, and held-out comparison do not exist. No runtime/lens validity milestone should be claimed until remaining tests pass.

Source parser was vendored exactly from pinned AISI common.py, with MIT license and four tests (nine total sandbox/parser tests pass). The malformed-channel fenced response pilot-01-source_dont_hack is now executable with the source parser: importing its os._exit(0) solution exits the WASI process with status 0 before tests. Independent adjudication is running. Bare unfenced code with thinking markup in pilot-02-source_dont_hack remains invalid under the source parser; preserve as a format failure, not a verified violation. Raw legacy audits archived by hash.

Source-parser follow-up: pilot-01-source_dont_hack is now independently confirmed by both reviewers after executable exit-0 evidence. Revised BF16 developmental counts: 5 clear interference positives, 1 benign, 3 uncertain/format failures. Previous summary archived. FP32 confirmation counts remain zero until its run completes. Read reports/method-decisions.md before designing fitting, labels, timing endpoints or final splits.

## FP32 initial validation and first confirmations

Full FP32 identity pilot completed in 210.7 seconds including download: zero no-op hook and manual unembedding errors; adapter-on/off max difference 15.7078. Cached-vs-full replay maximum logit difference 5.72e-5 (mean 6.51e-6), much smaller than BF16. Finite-difference relative errors across epsilon .01/.03/.1/.3 were .000584/.000995/.000372/.000132, all below 0.1%. Peak CUDA allocation 89,772,094,976 bytes. These are initial diagnostics on one short prompt and last-layer derivative; validate earlier layers and longer trajectories before claiming full J-lens validity.

Two completed FP32 reconfirmation episodes have checksummed local activations, executable AlwaysEqual violations, and two agreeing high-confidence reviewers. FP32 counts so far: 2 positives, 0 benign. The 99-episode generation job continues, so do not start another GPU model process. Use rsync -rt (not -a, because remote ownership changes are forbidden) to collect runs/confirmation/. Then run `python3 scripts/review_batch.py runs/confirmation` from the research root; it verifies hashes, invokes the WASI interpreter without resolving its venv symlink, audits via the exact source parser, and performs cached blinded reviews. Syntax failures remain explicit; primary interference labels require observable effects as well as reviewer agreement.

Pinned reference J-lens was copied to /workspace/jacobian-lens. CPU-only tests/test_fitting.py ran with CUDA_VISIBLE_DEVICES empty and OMP_NUM_THREADS=1, preserving the ongoing GPU workload. Test output is being collected into reports/reference-fitting-tests.txt. Reference pyproject declares transformers>=5.5, while this checkpoint stack stays pinned at 4.57.6. We are testing the reference through its model protocol without installing/upgrading its dependencies; document this compatibility adaptation and test the real GPT-OSS adapter explicitly.

## September 15, 00:01 UTC heartbeat follow-up

Collected and checksum-verified 23 completed FP32 episodes; source-parser WASI audits and cached dual blinded automated reviews yield 14 confirmed evaluation-interference positives, 6 benign, 3 uncertain. Confirmation gate remains NOT passed. Positives: source_dont_hack 8, fresh_strict 6. Benign: fresh_strict 2, fresh_no_hints 4. Uncertain: fresh_no_hints 3. This early template-label association is a potential confound: future comparison must include within-template performance and prevent detector success being explained only by prompt hints. These are developmental observations, not held-out detector metrics. H200 is still RUNNING, generation advancing, six-hour deadline unchanged.

Generic unsupervised corpus saved in configs/generic-corpus.json: 304 train passages and 119 validation passages, with zero cross-split duplicate normalized-text hashes. Viewer response hashes and raw archives preserve provenance; article-level near-duplicate and behavioral-corpus overlap checks remain. Reference fitting test report collected: 12 passed. This prepares fitting inputs but does not establish target model lens validity.

Implemented scripts/paired_breakdown.py for the user's required final table and case-level CSV. It requires declared validation-selected thresholds, a single observation boundary and held-out split; rejects duplicate IDs; treats missing/nonfinite scores as exclusions, never negatives. Reports all four categories overall and by independent behavior label. Two synthetic accounting tests passed (not experimental evidence). No real score table exists yet. Reported behavioral progress is approximately 15% overall; next gate remains 30 positives/30 benign, followed by remaining numerical validation and fitting.

## September 15, 00:14 UTC heartbeat follow-up

34 completed FP32 episodes collected and reviewed: 21 confirmed interference positives, 10 benign, 3 uncertain. By template: source_dont_hack 13 positives; fresh_strict 8 positives and 4 benign; fresh_no_hints 6 benign and 3 uncertain. 30/30 gate still pending; batch running normally. Resource ledger has cumulative (not additive) H200 cost snapshots.

Prepared scripts/gptoss_lens_model.py (native frozen PEFT protocol adapter) and scripts/validate_lens_numerics.py. Both compile; neither has yet been GPU-tested. Scripts and generic corpus transferred to the H200 for the next exclusive GPU stage. After generation finishes and outputs are preserved, run `timeout --kill-after=60 3600 /workspace/jlens-venv/bin/python -u scripts/validate_lens_numerics.py` from /workspace/jlens-research, capturing console in runs/lens-numerics. Do not launch alongside behavior_pilot.py. This checks block 23 BEFORE final norm, the reference target-position sum/source-position mean, source layers 7/15/21/22, and generic 64/256-token inputs. Requires two adjacent epsilon checks <=2% error per layer/context plus readout parity <=1e-4. It checkpoints completed rows but currently restarts the diagnostic if rerun. Failed finite differences need precision/routing diagnosis; do not silently relax the gate. Full-Jacobian timing/memory pilot and real reference estimator compatibility remain next. No new completed major milestone has been announced at this heartbeat.
