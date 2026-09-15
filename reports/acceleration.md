# Acceleration deployment

The user authorized useful speedups and additional costs on September 15, 2026.

Two H200 workers now run independent jobs. A separate 8-vCPU controller collects results directly between cloud machines, runs up to eight isolated audits/reviews, launches prepared fitting shards only after their gates pass, and stops tracked GPU pods at their deadlines. Current compute rates total $9.50/hour (2 × $4.59 + $0.32), excluding storage and API charges. Up to four GPUs are permitted, but further scaling waits for full-fit measurements. CPU controller storage is ephemeral and must be copied before terminating it.

The controller is a deterministic pipeline runner. Prepared computation and review can continue while the laptop sleeps. Codex research reasoning, unprepared stages, and updates in this chat still depend on the desktop.

## Measurements and validation

- Cache benchmark: three development prefixes, each tested over 33 decoding steps. Speedups were 19.18×, 13.35× and 7.84×, with maximum logit disagreement below 9e-5 and residual relative RMS disagreement below 3.4e-6. See `runs/speed-benchmark/report.json`.
- These short checks do not guarantee later trajectory parity. New generation performs full-prefix checks every 32 tokens and at EOS/token cap. Later divergence was observed; affected cached attempts are discarded and the full episode restarts uncached using the same seed. No failing cached trajectory is accepted. Actual mode and generator hash are recorded per episode.
- Jacobian batching: two dimensions per pass took 1.573 seconds for 32 rows, compared with 1.929 seconds for one dimension. This is 18% less time, or 23% higher throughput. Four and eight dimensions were slower in this benchmark. Estimated time for 2,880 rows is about 142 seconds per 64-token prompt; this is an extrapolation, not a measured full fit.
- Reference-reduction numerical checks passed all four selected source layers at 64 and 256 tokens. Each accepted pair of adjacent step sizes stayed within 2% derivative error with unchanged downstream expert sets. Earlier failed measurements remain archived; the refined diagnostic changes perturbation scaling and subtraction precision, not the target derivative or tolerance.
- The cloud WASI sandbox and source parser passed all nine tests. Controller credentials remain outside the repository and outside guest task capabilities. Generated code never runs natively on the controller or GPU host.

## Preserved scientific requirements

All current cases are development cases. The independent behavior gate, grouped held-out split, frozen thresholds, correct reference estimator, and the requested four-way paired detection table remain required. Two disjoint two-prompt fitting shards are prepared as a full-dimensional engineering pilot; four prompts do not establish convergence or final detection performance.

RunPod infrastructure fields were checked against the [official Pod API documentation](https://docs.runpod.io/api-reference/pods/POST/pods). The scheduler's accepted resource values and measured results are preserved in the local manifests and run reports.
