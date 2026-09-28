# Project status dashboard

Run from any directory:

```sh
python3 /absolute/path/to/reports/reader-comparison/dashboard/server.py --port 8766
```

Open `http://127.0.0.1:8766`. The page polls sanitized aggregate status every 15 seconds. The server binds only loopback, exposes an explicit artifact allowlist and never serves the repo, ledger records, credentials, or source code. It performs no inference or research mutations. It writes only the sanitized dashboard snapshot.

`python3 server.py --snapshot` refreshes the public `status.json` and embedded fallback inside `index.html`. The standalone HTML retains a dated snapshot without the server; its disconnected warning makes clear that it is no longer live.

The 12 milestones are explicit planning buckets, not effort weights or scientific certainty. Successful process exit alone never completes scientific closeout. Remaining evaluation/audit requires the review completion file and audit plus pipeline completion artifacts. Final integration remains pending until a dashboard-owned `final-integration.json` explicitly records `verified_complete: true` and a repo-relative existing `verification_artifact`. Create that record only after actual final document/package verification.

Sources are execution artifacts, independent of the Codex goal badge. Missing reads retain cached values with a stale indicator. Missing budget aggregates produce a service error instead of a zero-spend claim. A running-state coordinator with no matching live process raises an attention state. New review counts exclude cached successes and prior unavailable requests. Reserved costs include live calls and retained uncertainties; known prior uncertain charges are a subset, never double-counted.
