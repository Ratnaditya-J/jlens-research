# What each temporal endpoint can reveal

The current captures were audited on all 255 training and 126 validation episodes. The audit verifies stored prefix provenance and examines only generated text after the prompt boundary, so mentions of `true` and `false` in the task instructions do not count as disclosure.

| Endpoint | Training explicit choices | Validation explicit choices | Interpretation |
|---|---:|---:|---|
| End of prompt | 0/255 | 0/126 | Before response generation |
| Before action | 0/255 | 0/126 | At the prompt boundary on these splits |
| −32 and −64 token controls | 0/255 each | 0/126 each | Earlier prompt positions on these splits |
| During action | 0/255 | 0/126 | Response has begun; the Boolean choice is not yet explicit |
| After action | 255/255 | 126/126 | Complete Boolean choice is already visible |

During-action readouts include 5–11 generated tokens in training and 6–10 in validation. Neither a complete Boolean nor a partial spelling that uniquely distinguishes `true` from `false` is visible. The probe/readers can still exploit other textual cues; this is why text-only baselines and correct/shuffled-context controls remain necessary.

After-action performance measures recognition of an already expressed choice, not advance detection. Strong after-action performance alone would not demonstrate access to a hidden misaligned intention. Conversely, a weak pre-action result does not establish that the relevant information never becomes available.

This is a descriptive audit of development splits. It neither reports held-out temporal detector performance nor changes the frozen endpoints, labels, models or thresholds. Held-out visibility should be reported alongside the completed temporal evaluation. The full project and remaining comparisons remain in scope.

Reproduce from the repository root:

```sh
../jlens-review-venv/bin/python studies/reader_comparison/audit_visible_action_value.py \
  --features runs/reader-comparison/features-before_action/manifest.json \
  --captures runs/reader-comparison/production-captures \
  --out studies/reader_comparison/evidence/train-validation-action-visibility.json
```

The machine-readable output records per-episode classifications and capture/source hashes. Three tests cover field-name false matches, complete and partial Boolean values, and prose/invalid-value controls.
