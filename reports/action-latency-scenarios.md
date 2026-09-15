# Action-timing latency scenarios

The current API-interpreted J-lens does not establish a timely warning before the localized violating source statement in the selected cases. All its flagged localized cases have negative estimated time margins after display and review latency. This is a latency limitation of this interpretation procedure, not proof that J-space contains no earlier information.

| Endpoint | Localized selected cases | Probe flags / positive warm margins | J-lens flags / positive margins |
|---|---:|---:|---:|
| 0 tokens before code onset | 3 | 3 / 3 | 3 / 0 |
| 32 tokens before code onset | 12 | 6 / 6 | 6 / 0 |
| 64 tokens before code onset | 12 | 6 / 6 | 6 / 0 |

These rows are separately selected casebooks and may reuse episodes; do not add them as independent observations. A flag here is not automatically a correct detection. This is not a population sensitivity table.

We sum recorded generation time for the full intervening steps, excluding the scored and localized-statement token steps. Probe cost uses the measured warm primary linear-score p95 on an already resident CPU activation. Earlier linear probes reuse that cost as an assumption. J-lens cost includes its measured display time and the slower of its two recorded review calls, assuming simultaneous requests. Queuing, activation transfer and contention are omitted. A second scenario adds measured replay latency: positive probe margins become 1/3 at code onset and remain 6/6 at each earlier endpoint; J-lens remains zero.

The localized boundary is generation of a source statement subsequently implicated by the execution audit. It is not the time of execution, intent formation, or a verified first commitment. Real-time deployment and earliest warning remain unmeasured. All source hashes, per-case values and assumptions are in `action-latency-scenarios.json`.
