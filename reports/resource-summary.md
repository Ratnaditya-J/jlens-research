# Resource audit

Snapshot: 2026-09-15T05:46:54.130721+00:00

Active project GPUs: **0**. The CPU controller remains active for the remaining work.

Retained successful reviewer responses: **12,198**, deduplicated by response ID across copied archives.

| Route / reviewer | Responses | Prompt tokens | Completion tokens | Reported response cost |
|---|---:|---:|---:|---:|
| direct OpenAI / gpt-4.1-2025-04-14 | 5,671 | 14,466,419 | 960,442 | Unavailable |
| direct OpenAI / gpt-5.4-2026-03-05 | 5,678 | 14,470,715 | 1,657,885 | Unavailable |
| OpenRouter / openai/gpt-4.1 | 424 | 1,152,556 | 70,831 | $2.8637 |
| OpenRouter / openai/gpt-5.4 | 425 | 1,156,190 | 113,655 | $4.5953 |

The latest sessions visible for 12 project pods account for 14.97 GPU-hours. Summing each visible latest session’s listed rate times duration gives approximately $70.55, including CPU sessions. **This is not the study’s total bill.**

- Pod estimates cover only the latest provider-reported start/stop interval; they are not lifetime invoices and must not be added to cumulative ledger snapshots.
- Stopped-volume storage, terminated-pod history, taxes and other charges are not reconciled here.
- Reviewer counts deduplicate response IDs across retained archives; failed/unretained requests, diagnostic pings and this Codex conversation are excluded.
- Reported OpenRouter costs are available only where returned in usage; direct-API dollars are not invented from missing billing data.

The complete snapshot and response-source hashes are in resource-audit.json; the event ledger records the report hash. Do not add this snapshot to prior cumulative ledger snapshots.
