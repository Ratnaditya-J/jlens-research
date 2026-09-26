# Training-activation lens-fit stability

Descriptive pre-action diagnostics on32 unique training states per layer. Corpus halves are disjoint; task states are not assumed independent. No behavioral labels or held-out outcomes were analyzed.

| Layer | First16 vs primary32 median cosine | Disjoint16 vs16 median cosine | Disjoint relative error (aggregate) |
|---|---:|---:|---:|
| 20 | 0.9714 | 0.8896 | 46.7% |
| 36 | 0.9785 | 0.9081 | 44.8% |
| 48 | 0.9939 | 0.9757 | 22.0% |
| 60 | 0.9992 | 0.9968 | 8.1% |

The early layers show greater finite-sample variation than the late layer. These are transported residual-vector comparisons before final normalization/unembedding, not token agreement or semantic accuracy. The nested comparison shares fitting data and is more optimistic than the disjoint comparison. The fixed32-passage primary fit is unchanged. This supports explicitly limiting future blind-spot claims to the fitted instrument; it does not establish a blind spot or absence of information from an ideal J-space.

See `training-activation-fit-stability.json` for source hashes, runtime versions, quantiles and numerical recomposition checks.
