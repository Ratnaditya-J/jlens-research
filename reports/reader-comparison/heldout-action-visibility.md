# Held-out action visibility audit

All 128 held-out episodes were checked across six endpoints and four capture layers. Capture manifests and per-episode cell hashes were verified, and all four layers shared the same prefix and position for each endpoint. This is a descriptive audit after primary held-out results were inspected; it does not fit detectors or choose thresholds.

At the during-action endpoint, 0/128 prefixes contain the complete Boolean action value or an unambiguous partial spelling of it. At the after-action endpoint, 128/128 contain the complete Boolean value. Accordingly, after-action detection is recognition with the explicit choice already visible; it cannot support a claim of advance warning. During-action detection precedes the explicit Boolean choice, but other textual cues may already reveal the intended decision.

Unlike the training/validation trajectories, two of the 128 held-out trajectories contain generated text before the action marker; the other 126 do not. Visible generated-token ranges are 0–88 before action, 0–56 at minus32, 0–24 at minus64, 5–96 during action, and 10–104 after action. End-of-prompt has zero generated tokens. Token offsets are relative to the action boundary, not uniformly relative to the prompt boundary. Matched text baselines remain necessary when interpreting activation signals.

These checks establish lexical visibility, not absence of intent in text, faithfulness of either lens, or detector effectiveness. The original training/validation audit and frozen analysis code remain unchanged. The full temporal comparison still requires completed validation reviews, locked thresholds, and held-out reviews with explicit missingness.

Reproduce from the repository root:

```sh
../jlens-review-venv/bin/python studies/reader_comparison/audit_heldout_action_visibility.py --features runs/reader-comparison/features-before_action/manifest.json --captures runs/reader-comparison/production-captures --out studies/reader_comparison/evidence/heldout-action-visibility.json
```
