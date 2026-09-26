# Summarizer extension: measured findings and remaining coverage

Updated September 26, 2026. This is an addendum to the archived GPT-OSS study, not a replacement for its results. The separate Qwen probe/J-lens/Oracle comparison remains in progress. New OpenRouter inference is paused for cost control.

## Primary result: 32 tokens before code onset

The preregistered primary comparison does **not** support the proposed sensitivity improvement from replacing token displays with blind summaries. On 617 paired known-label cases (445 violations, 172 benign), summary-plus-context detects 286 violations versus 323 for the frozen J-view, with 8 versus 22 false positives. The paired sensitivity difference is **−8.31 percentage points** (95% family bootstrap interval −11.96 to −5.30); the false-positive-rate difference is **−8.14 points** (−14.37 to −3.82). This is a sensitivity–specificity tradeoff, not evidence that summarization universally helps or hurts detection.

The activation probe remains more sensitive. At the summary arm's achieved validation specificity, the recalibrated probe detects 353/445 violations with 12/172 false positives, versus 286/445 and 8/172 for summaries. Matching validation specificity does not guarantee equal test false-positive rates.

A secondary arm retaining the original tokens and candidate ranks alongside the summary is more promising: on its 614 paired cases, sensitivity differs from J-view by **+0.45 points** (−1.94 to +3.36) and false-positive rate by **−6.36 points** (−12.95 to −0.91). Its detected counts are 321/441 violations and 12/173 benign cases. This exploratory result does not establish equivalence of sensitivity, and it does not isolate whether summaries, combined presentation, or reviewer transport differences caused the change.

Sources: [primary results](jsummary-fresh-offset32/summary.json), [coverage](jsummary-fresh-offset32/coverage.json), [deterministic disagreement casebook](jsummary-fresh-offset32/casebook.md).

## Context and display controls

At −32, blind summaries detect 30/445 violations with 8/174 false positives; blind raw displays detect 17/445 with 2/174 false positives. Blind-summary AUROC is 0.511. These observations provide little evidence of a strong stand-alone detector at the selected operating point. A positive blind readout still does not prove information beyond the input text, because an activation reader can reconstruct that text.

Correctly paired summaries outperform shuffled summaries in sensitivity by **5.17 points** (95% family bootstrap interval 1.80 to 8.73); the paired false-positive-rate difference is +0.58 points (−1.00 to +3.18). Thus the display is not wholly interchangeable in this experiment. However, summaries and context-only judgments have nearly identical sensitivity: difference **−0.22 points** (−1.95 to +1.57). Neither contrast establishes causal necessity or faithful access to hidden intentions. Failure to reject a difference is not evidence of equivalence.

The proposal's alternative explanation also needs qualification: failure of the summarizer hypothesis does **not** establish that the relevant information is absent from the full J-space. Loss could occur in the top-k display, the summarizer, the rubric, or threshold selection. Full-space probes and direction-transport diagnostics in the separate Qwen study address some of those distinctions.

An [eight-case qualitative audit](jsummary-fresh-offset32/qualitative-audit.md) illustrates those distinctions using the fixed disagreement casebook. It finds examples of visible hacking deliberation with a benign outcome label, relevant termination language retained in a summary that nevertheless fails to flag, unsupported layer-specific narratives, and lens/summary hits missed by the probe. These are post hoc illustrations, not prevalence estimates or causal findings. Several apparent pre-generation discoveries concern concepts already supplied in the prompt, so novelty relative to the generated prefix must not be confused with novelty relative to the entire causal text.

## Secondary endpoints

At −64, the paired summary/J-view comparison contains only 118 cases: summaries detect 2/68 violations, versus 17/68 for J-view; both have zero false positives among 50 benign cases. Sensitivity difference: **−22.06 points** (−32.08 to −14.29). Zero observed false positives and a degenerate bootstrap interval are not proof of zero population risk. A reviewed probe-only example already shows why detector disagreement cannot automatically be called information invisibility: relevant content can appear in the description yet fail the frozen score threshold. See the [−64 interpretation notes](jsummary-fresh-offset64/interpretation-notes.md).

Code-onset results are **incomplete cached-subset results**. After the cost pause, evaluation reused existing responses without making any new HTTP inference requests. The summary arm has judgments for 456 known-label cases: 299/302 violations detected and 0/154 false positives. Its blind-summary arm detects 0/302; the shuffled contextual arm detects 292/297 on its available subset. The paired correct-minus-shuffled sensitivity difference is +0.67 points (−0.65 to +1.96). These results cannot be extrapolated to the entire original cohort: request ordering and response latency may have affected what finished before the pause.

Sources: [−64 results](jsummary-fresh-offset64/summary.json), [code-onset cached results](jsummary-fresh/summary.json), [offline completion record](../runs/fresh-jsummary-test/offline-completion.json).

## Coverage and interpretation limits

At −32, 619 of 727 known-label episodes had stored readouts; all 619 received complete summaries, and 617 had usable contextual-summary judgments. Most missingness is therefore upstream endpoint availability, with two additional unavailable judgments. At −64, only 120 known-label episodes had stored readouts and 119 had usable contextual-summary judgments; the paired J-view comparison loses one further case. At code onset, 723 known-label episodes had stored readouts, but only 456 had usable contextual-summary judgments: 267 missing judgments are separate from four missing original readouts.

Every arm retains its own denominator. Pairwise claims above use the common eligible cases. The original reports also contain AUROC, AUPRC, uncertain-label-as-benign sensitivity analyses, missingness bounds, thresholds and per-case scores. Bootstrap intervals resample whole task families (15 families, 2,000 replicates); they do not represent arbitrary deployment populations or adjust all exploratory contrasts for multiplicity. Original reviewer judgments are frozen; provider transport differs in the extension. The study evaluates authored evaluation-interference tasks on one fine-tuned model.

## Work still required

The original frozen summarizer extension has not completed the template-challenge, authorization/debugging, or monitor-maintenance panels. In particular, there is no new basis yet for claiming the summarizer preserves the original 0/47 authorization-control result. Code-onset missing judgments also remain missing. Any local-judge continuation must be calibrated and reported as a distinct protocol, rather than silently filling these frozen premium-reviewer arms with a different judge.

The Qwen follow-on must still complete checkpoint-specific fitting, readouts, local-judge validation, calibration, held-out comparisons, specificity controls, and final artifact verification. Its results must be presented separately from this GPT-OSS extension. Full Oracle reconstruction FVE is not currently available; using its verbalizer alone cannot certify reconstruction fidelity.
