# Native grouped fusion provider

`scripts/amber_fusion.py` adds logistic stacking over the existing portable text
and activation monitor fits. It accepts training observations only, with explicit
episode, template and matched-pair identities. A component receives only its
allowed text view or activation vector; grouping and oracle metadata never enter
its feature values. The initial implementation supports output, raw reasoning,
activation and the context control. Verified paraphrase integration remains a
separate requirement.

Template and pair connections are merged transitively into indivisible groups.
A fixed seed orders group hashes; round-robin assignment gives the requested
fold count without consulting labels, scores or class balance. Each native
component is refitted outside the held group. Those out-of-fold margins train
the standardized logistic stack; its coefficients are exported back to the
original margin scale. Final component fits use every eligible training row
through the unchanged `amber_monitor.fit` implementation.

This follows the separation between out-of-fold meta-training and full-training
component refits described in the [scikit-learn stacking documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.StackingClassifier.html).
The grouping requirement follows the [grouped cross-validation guidance](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data).
The implementation uses the native portable monitor exports, explicit folds and
an auditable record of every component fit, rather than serializing estimators.

Unknown labels and absent channels remain in the input and exclusion records.
Only complete, known-label observations train the stack; each component may use
its own additional eligible rows. There is no missing-value imputation. A fold
without both training classes fails; seeds/folds are not silently retried. The
export includes all assignments, fold-specific fit artifacts, held-out training
scores, final component fits, runtime version and hashes.

These out-of-fold scores train the stack and cannot evaluate it. Deployment must
bind the stack to the exact final component identities, abstain when an input is
missing, and freeze its operating points on separate benign calibration data.
Neither group assignment nor passing portable numerical replay establishes
template independence, statistical power, adaptation robustness or efficacy.

Run the twelve focused provider checks:

```sh
python -m unittest discover -s tests -p 'test_amber_*.py' -v
```
