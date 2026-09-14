# J-lens and probe comparison status

Persistent execution is active via the Codex heartbeat `j-lens-and-probe-research`, every 30 minutes. The user authorizes autonomous decisions and paid execution, with replenishing balances. Do not ask routine implementation or balance questions.

## Completed

- Read the execution brief, saved its text in `../../work/brief.txt`.
- Verified RunPod authentication and available 80 GB GPU stock.
- Pinned AISI adapter `9e11602b9e67211887229ed20d0ac79e412ee910` and Unsloth BF16 base `cc89b3e7fd423253264883a80a4fa5abc619649f`.
- Pinned reference J-lens code `581d398613e5602a5af361e1c34d3a92ea82ba8e` and AISI evaluation code `169c3c76a02e51092b4023a8c7baba38f41e2800` under `../../work/upstream/`.
- Archived Hugging Face metadata and configs in manifests. Adapter rank/alpha are 32, targeting q/k/v/o projections. Base weight download is about 42 GB.

## Current gate

Stage 0: executable identity and GPU compatibility. No behavioral result, fitted lens, or probe exists yet. Source checkpoint-to-result mapping remains unresolved; do not attribute published rates to this artifact.

## Next actions

1. Pod `cvwo3adm7a2a20` provisioned: A100-SXM4-80GB at $1.59/hour. SSH details in runs/pod.json; private key ../../work/private/pod_ed25519. Watchdog is running in exec session 83502. Poll, collect, and stop/terminate this pod before replacing it.
2. GPU pilot transferred to /workspace/jlens-research and launched with scripts/bootstrap_gpu.sh. Inspect runs/identity/progress.json, console.log, report.json or error.txt remotely, then download results. Download safetensors and tokenizer/config assets only; load BF16 base with active adapter; test logits, activation hooks, and differentiability. Preserve exact dependency versions and output hashes.
3. Inspect source evaluation prompts and configs. Implement isolated executable behavioral tasks and three scenario templates, retaining all attempts. First reproduce source conditions, then use fresh scenarios. Explicitly requested hacking is a separate elicited-capability condition.
4. Implement independent blinded adjudication using two API reviewers and external tests; preserve the automated-vs-human limitation.
5. Reach at least 30 verified positives and 30 benign episodes before interpretive comparison. Fit the genuine reference Jacobian estimator with a disjoint generic corpus; validate finite differences, replay, and convergence before using it.
6. Train leakage-controlled regularized logistic regression. Freeze test split, pre-action endpoint, 5% validation FPR threshold, and independent J-space rubric. Compare paired sensitivity, specificity, timing and disagreements with clustered uncertainty. Never manufacture a definitive result.

Read configs/resources.json on every continuation. Collect tracked job outputs before provisioning another GPU. Update this file after each stage. Consult manifests and runs rather than relying on conversational memory.
