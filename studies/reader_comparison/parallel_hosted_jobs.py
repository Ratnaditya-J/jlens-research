"""Bounded concurrent singleton invocations of unchanged registered readers."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from smoke import write_json

def run_wave(candidate, jobs, runner, out, credential_file, budget_file, workers=8):
    if not 1 <= workers <= 8 or not 1 <= len(jobs) <= workers:
        raise ValueError('At most eight concurrent requests per bounded wave')
    if len({j['request_id'] for j in jobs}) != len(jobs):
        raise ValueError('Duplicate request in wave')
    out=Path(out)
    if out.exists():raise ValueError('Preserve previous wave; no retry')
    out.mkdir(parents=True)
    def one(job):
        # Each runner keeps its registered singleton execution. The outer
        # scheduler owns concurrency, recorded separately from reader identity.
        work=out/job['request_id'];work.mkdir()
        jp=work/'jobs.json';write_json(jp,{'jobs':[job]})
        runner(candidate,jp,work/'reader',credential_file,budget_file)
        return job,work/'reader'
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # On failure, drain in-flight workers before allowing another wave.
        return list(pool.map(one,jobs))
