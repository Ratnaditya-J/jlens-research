# Current project execution constraints

The user's September26 cost correction supersedes earlier broad spending discretion for OpenRouter inference.

- New OpenRouter inference is paused while cost controls and local judging are implemented. Do not restart `scripts/continue_jsummary.py` or any previous uncapped review process.
- Retain and reuse all cached responses. The original primary −32 and secondary −64 summarizer evaluations are complete; do not rerun them.
- Any additional OpenRouter inference must use `studies/reader_comparison/budgeted_api_client.py` with the persistent budget ledger at `../../work/reader-runtime/openrouter-budget.json` (resolve relative to this repository). The additional project ceiling is $10. The ledger remains paused until a concrete small audit is justified; default to local inference on existing GPUs.
- Do not silently replace judges inside a frozen comparison. Register a distinct local/cheaper judging protocol, validate and calibrate it before held-out evaluation, and disclose the change.
- GPU fitting, captures, Oracle reading, probes and analysis continue. Preserve the full research objective, substantive controls and coverage reporting.
- Code discovery should prefer the codebase-memory MCP graph tools; use file search when graph results are insufficient or for non-code files.
