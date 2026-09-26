# Temporal lens-fit sensitivity on training activations

Disjoint16-passage lens fits, with exact duplicate states removed within each layer and endpoint. This is a descriptive fit-sensitivity analysis, not a misalignment detection result.

| Endpoint | Unique states per layer | L20 median cosine | L36 | L48 | L60 |
|---|---:|---:|---:|---:|---:|
| before_action | 32 | 0.8896 | 0.9081 | 0.9757 | 0.9968 |
| during_action | 101 | 0.8149 | 0.9298 | 0.9768 | 0.9968 |
| after_action | 114 | 0.8437 | 0.9433 | 0.9755 | 0.9971 |

The disjoint estimates differ most at layer20 across all three time points. Agreement at layer60 is higher, but does not establish semantic fidelity or detection performance. The first16-to-primary32 comparison shares fitting data and is systematically more optimistic. Magnitude errors and source hashes are in the corresponding JSON reports.

These results do not select or replace the primary32 lens, change layer selection, or inspect held-out performance. A detector miss must remain a claim about this fitted lens and the chosen readout, not proof that an ideal J-space lacks the information. Token-rank sensitivity has not been measured by this vector analysis.
