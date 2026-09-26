# Oracle Lens: source definition and this experiment's scope

## Primary definition

The primary source is the **Oracle lens** appendix of [Verbalizable Representations Form a Global Workspace in Language Models](https://transformer-circuits.pub/2026/workspace/) (Anthropic, July 6, 2026; accessed September 26, 2026).

The method decodes an activation into free-form phrases. A separately trained reconstructor maps phrases to activation directions. The oracle is trained using phrase decompositions and refined with a reconstruction objective. Full inference includes mapping sampled phrases back to directions and fitting nonnegative reconstruction coefficients. The paper's experiments use Haiku 4.5; their reconstruction results do not establish performance for our Qwen derivative.

An activation-to-text readout is therefore only one component of the complete method. “Oracle” is a method name, not a guarantee of truthful or exhaustive access to internal content. A missing concept cannot, by itself, establish absence of that concept from an activation.

## Open implementation references

- [WorkspaceBench](https://github.com/camilablank/workspace-bench) describes its O-lens as a LoRA verbalizer that produces sentences from an activation. This is the operational use closest to our experiment.
- [Released adapters](https://huggingface.co/agu18dec/olens_and_ar): our pinned reader is `olens_s3d_rl600` at revision `c95215d5d2f6250f20c305ae55c6e4d7569f92dc`.

## What our code actually runs

The authoritative configuration is `config-em-riskyfin.json`; inference is implemented in `oracle_read.py`. The code loads saved activations from the exact fine-tuned subject and verifies their identity and hashes. A separate base-model copy carries the Oracle adapter; it does not also carry the subject adapter. The captured vector is normalized and scaled by the configured alpha, then injected at the carrier embedding position. The reader generates descriptions with one sampled readout per unique layer/state combination; identical states share the same readout.

The implementation verifies adapter tensors and checks that enabling the adapter changes logits. These are engineering checks. They do not validate semantic accuracy or transfer to the fine-tuned subject.

We do **not** run the reconstructor, pooled whitening, coefficient refitting, or a full reconstruction-based fraction-of-variance evaluation. The configuration explicitly retains `subject_transfer_validated: false`. The small topic-transfer check and random-direction controls are limited diagnostics, not certification of semantic faithfulness.

## Naming and reporting rules

Use **Oracle Lens verbalizer readouts** for this experiment's arm. Reserve **full Oracle Lens reconstruction** for the complete procedure. Report observable detection performance and coverage on independently labeled episodes, with context-only and shuffled controls; do not call the verbalizer a ground-truth judge. Keep three possible failure sources separate: missing information in the readout, a downstream text judge failing to recognize information, and unavailable or malformed output. The supervised probe and J-lens comparison must retain these distinctions in casebooks and uncertainty reporting.
