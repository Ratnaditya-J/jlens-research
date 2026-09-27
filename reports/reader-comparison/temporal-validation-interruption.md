# Temporal validation review interruption

The continuation terminated after seven GPT-5.4 Flex HTTP 502 provider-unavailable responses. There are 363 usable GPT-4.1 requests and 356 usable GPT-5.4 requests, plus seven explicit unavailable GPT-5.4 requests. Each reader has 597 never-attempted requests remaining out of the fixed 960-request union.

All 345 newly successful responses were receipt-verified. Failed requests retain their reserved charges; no retry, provider substitution, or threshold fitting occurred. The ledger is paused at $8.423517 settled and $0.780067 reserved, leaving $0.796416 within the $10 ceiling. These are additional-budget figures, not total historical project cost.

## Coverage by endpoint and arm

| Endpoint | Arm | Usable pairs | Provider unavailable | Missing summary | Pending |
|---|---|---:|---:|---:|---:|
| during_action | j_tokens | 44 | 0 | 0 | 82 |
| during_action | j_summary | 59 | 1 | 2 | 64 |
| during_action | oracle | 40 | 0 | 0 | 86 |
| during_action | context_only | 37 | 0 | 0 | 89 |
| during_action | j_tokens_context | 54 | 0 | 0 | 72 |
| during_action | j_summary_context | 56 | 2 | 2 | 66 |
| during_action | oracle_context | 65 | 0 | 0 | 61 |
| during_action | j_summary_shuffled_context | 44 | 0 | 1 | 81 |
| during_action | oracle_shuffled_context | 44 | 0 | 0 | 82 |
| after_action | j_tokens | 27 | 2 | 0 | 97 |
| after_action | j_summary | 61 | 1 | 0 | 64 |
| after_action | oracle | 37 | 1 | 0 | 88 |
| after_action | context_only | 35 | 1 | 0 | 90 |
| after_action | j_tokens_context | 58 | 0 | 0 | 68 |
| after_action | j_summary_context | 45 | 0 | 0 | 81 |
| after_action | oracle_context | 57 | 2 | 0 | 67 |
| after_action | j_summary_shuffled_context | 47 | 0 | 0 | 79 |
| after_action | oracle_shuffled_context | 44 | 0 | 0 | 82 |

Each row contains 126 validation episodes. Shared requests can affect multiple aliases; counts are not independent replications. Pending entries cannot be treated as negative predictions.

No full temporal calibration or held-out comparison is complete. A continuation must preserve these unavailable requests, the original summary timeout, the exact accepted reader protocol and remaining request identities. Completion of the full comparison is not funded by the remaining allowance based on observed review costs.
