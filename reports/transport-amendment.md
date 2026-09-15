# Secondary timing reviewer transport amendment

The direct OpenAI endpoint returned HTTP429 with code `credit_balance_exhausted` and type `insufficient_quota` while the 32-token-earlier held-out interpretation was nearing completion. The primary, template and specificity comparisons had already completed. Their nine frozen output hashes remain unchanged.

User authorization covers OpenRouter. Its authenticated endpoint is available. The model catalog maps openai/gpt-4.1 to canonical slug openai/gpt-4.1-2025-04-14 and openai/gpt-5.4 to openai/gpt-5.4-20260305. Supplemental requests restrict routing to provider OpenAI with fallbacks disabled. The response must identify the expected routed model and OpenAI provider. This mapping does not establish bitwise equivalence to direct-API execution.

`scripts/interpret_fresh_openrouter.py` preserves every existing cached judgment and its logical request hash. It sends only missing requests, with unchanged evidence, rubric, score definition and response format. It translates max_completion_tokens to max_tokens and reasoning_effort to the gateway reasoning.effort field. Both logical and actual sent requests, their hashes, returned model/provider and catalog mapping are preserved. The original aggregation/input manifest remains the base contract; the supplemental producer is separately identified in transport-manifest.json and each new review. Prior incomplete scores and completion records are archived by hash before supplementation.

No primary threshold, probe weight, original label or successful direct-API response is changed. Earlier-endpoint validation/test counts and provider composition must be reported, including a direct-API-only available-case sensitivity analysis. Any offset64 interpretation uses the same explicitly amended transport if its training/validation support gate passes. The timing results are secondary; matching catalog snapshots alone does not justify suppressing transport uncertainty.

Reference for the gateway reasoning parameter translation: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens .
