# Earlier-token validation calibration

Both accepted reviewers completed all 288 unique requests: 288/288 usable each. Each endpoint contains all 126 validation episodes and all nine reader arms without unavailable judgments. The original calibration algorithm has frozen separate −32 and −64 locks; all source hashes were reverified.

All arms have 53 available prohibited-condition benign validation examples and zero observed false positives at the selected threshold. This is a finite validation result, not a population specificity guarantee or held-out detection result.

At −32, J-summary with context, Oracle with context, and shuffled J-summary with context have thresholds strictly above 2, the maximum reader score. These operating points necessarily flag no cases. They remain frozen; switching thresholds to obtain detections would invalidate the planned comparison. Continuous ranking metrics can still be evaluated independently of this threshold limitation.

The −64 reader thresholds are at score 2 except context-only, which flags scores of at least 1. Raw/J-transformed probe and text thresholds are preserved in the evidence JSON. Selection and calibration use training/validation only. Primary held-out outcomes had already been examined before these additional locks, so the chronology must remain disclosed; the algorithm, cohorts, and commands were fixed in advance, and no earlier-endpoint held-out metrics have been evaluated here.

The separate registered during/after-action validation-summary phase has begun under the unchanged cumulative $7 allocation. Earlier held-out comparisons, temporal readout comparisons, legacy controls, and final synthesis remain incomplete.
