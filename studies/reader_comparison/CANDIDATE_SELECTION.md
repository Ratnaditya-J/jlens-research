# Subject selection record

Production subject is not selected merely from model names or automated labels.

- **Initial compatibility subject:** LASR-Callum difficult-advice/TULU adapter, pinned in config.json. This is an alignment-oriented fine-tune with reported residual violations. Oracle capture/reading and FP32 derivative checks work. The initial fresh behavior screen includes truncations, first-read-only responses, and an authorization-disputed shutdown override. These do not yet justify a large detection study.
- **EM-insecure candidate:** Jordine/em-qwen3.6-27b-insecure. Stopped during loading, before generating screening trajectories, after inspecting the author's actual results: only 0.7% misaligned-of-coherent on the published eight-question screen. Name alone was an insufficient selection criterion.
- **Current second candidate:** Jordine/em-qwen3.6-27b-riskyfin, revision 6048234d8ad9efb91931f275e801151180fe57e8. The author's phase-0 results report 800 answers, 95.5% coherent, 36.12% coherent-and-misaligned overall, and 37.83% misaligned among coherent answers. These are broad emergent-misalignment scores on eight question families, not a measured agentic violation rate. Fresh agentic behavior and Oracle transfer still require validation.

Source: https://github.com/Jordine/sdf_can_detangle_em, inspected revision d48a13e6485754ac8043648884b9f0ded8b8fe32, phase0/RESULTS.md and results/em-qwen3.6-27b-riskyfin_judged_summary.json, with raw per-answer records. Its published training and generation disable thinking; the new candidate screen follows that setting. The initial compatibility subject was screened with thinking enabled, so those screens must not be treated as a controlled causal comparison of adapters.

The one-prompt engineering J-lens belongs only to the initial compatibility subject. It must never be relabeled or reused as a fitted lens for the risky-financial-advice adapter.
