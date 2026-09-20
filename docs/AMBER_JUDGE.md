# AMBER frozen authorization judge

`scripts/amber_judge.py` owns the versioned rubric, strict request schema and
assessment validation. It has no credentials or network calls. AMBER owns API
execution, bounded reservations, source sealing, view construction and replay.
The policy supports the simulated authorization-execution mechanism only.

All views use identical instructions/schema. Output gets public context, final
answer and action trace; raw CoT additionally gets scratchpad; context-only gets
public context. IDs, labels, splits, template metadata and model scores are rejected.
The judge returns an uncalibrated risk score and a short evidence summary. Missing
or invalid judgments abstain. The environment remains the only oracle authority.

Model snapshot, API backend, caps, pricing, rubric hash and provider commit must
be frozen in each AMBER run. Calibration requires independent benign episodes;
diagnostic probes and successful schema checks establish neither efficacy nor FPR.

Version 2 clarifies that the monitored subject is the auditor, not the producer
who supplied the proposed update. It adds fixed approve/block examples and an
explicit distinction between detection and execution. The response schema is
unchanged. This revision follows observed development construct errors; old scores
remain attached to v1 and repeating those cases is not independent validation.
