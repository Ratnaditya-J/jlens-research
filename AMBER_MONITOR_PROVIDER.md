# AMBER frozen monitor extension

`scripts/amber_monitor.py` exposes JSON stdin/stdout `fit` and `predict` operations
for the existing fixed development pipelines: standardized logistic activation
probe, and unigram/bigram TF-IDF logistic text controls (C=1, lbfgs, 3,000 iterations).
It extends this provider rather than copying study fitting code into AMBER core.

Fits accept only explicitly marked training rows, unique IDs, complete boolean
labels and both classes. Text fields have arm-specific allowlists. Preprocessing
fits only on these rows. Calibration, layer selection, hyperparameter search and
held-out evaluation are not performed. Callers must preserve excluded/missing rows
in their run ledger and enforce the prospective split manifest.

Exports are JSON numeric coefficients, vocabulary and IDF, never executable pickle.
Standardization is folded into activation coefficients. Exported margins must
match the native pipeline within 1e-8. This is numerical replay, not efficacy.
A scikit-learn version change requires a fresh verified artifact. Convergence
warnings fail the fit. The runtime and training-input hash enter each artifact.

Run `python -m pytest tests/test_amber_monitor.py` with NumPy and scikit-learn.
