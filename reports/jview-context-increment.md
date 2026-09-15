# J-view versus context-only interpretation

This post-hoc audit uses the existing frozen endpoint thresholds and paired cases. It does not retune either interpretation arm or establish matched-specificity superiority.

| Endpoint | Positive cases: J only / context only / both / neither | Benign cases: J only / context only / both / neither |
|---|---|---|
| Code onset | 0 / 0 / 464 / 0 | 2 / 6 / 1 / 250 |
| 32 tokens earlier | 37 / 1 / 286 / 121 | 12 / 1 / 12 / 149 |
| 64 tokens earlier | 2 / 11 / 15 / 40 | 0 / 1 / 0 / 48 |

At 32 tokens earlier, adding J-space to the interpretation arm yields 36 net additional detected violations among 445 positives, with 11 net additional false positives among 174 benign cases. Whole-family bootstrap intervals for the rate differences are approximately +5.2 to +11.0 percentage points in sensitivity and +2.0 to +12.6 points in false-positive rate. Thresholds have different attained specificity; this is a tradeoff, not a demonstrated free gain.

Of the 21 J-view-only true positives relative to the probe at that endpoint, 18 were also flagged by context-only interpretation. Only three were missed by both the probe and context-only arm. At 64 tokens earlier, all ten J-view-only true positives relative to the probe were also context-flagged. Thus the J-versus-probe disagreement count alone overstates the number uniquely attributable to the J-view arm relative to available text.

The 64-token comparison contains 117 known paired cases because two additional benign cases lack context judgments; they are excluded, never assumed negative. Its J-view sensitivity is lower than context-only at these frozen thresholds. Code onset shows no additional positive coverage from J-view because context-only already detects all observed positives.

These results do not prove which individual internal features caused a judgment. The arms differ in supplied evidence and prompt framing; no causal intervention or independent human-readability test was performed. Full per-case data, exclusions, bootstrap details and input hashes are in `jview-context-increment.json`.
