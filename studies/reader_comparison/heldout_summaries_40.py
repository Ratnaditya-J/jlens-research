"""Separate standard-route qualification; no mixing with accepted Flex outputs."""
import argparse
import json
import math
from pathlib import Path
from audit_budgeted_reader import fixture_jobs, pause_budget
from budgeted_api_client import file_lock
from budgeted_hosted_lowreference import payload, reservation
from hosted_text_reader_lowreference import execution_manifest, run_jobs
from contracts import fingerprint
from smoke import digest, write_json


def main():
    p = argparse.ArgumentParser()
    for n in ['budget-file', 'credential-file', 'out']:
        p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    candidate = 'gpt54lowreference'
    preflight_path=Path('studies/reader_comparison/evidence/heldout-summary-union-preflight.json')
    preflight=json.loads(preflight_path.read_text())
    for path,sha in preflight['source_hashes'].items():
        if digest(path)!=sha:raise ValueError('Held-out prepared source changed')
    for e in ['during_action','after_action','before_action_32','before_action_64']:
        prefix='standard' if e in ['during_action','after_action'] else 'accepted'
        lp=Path('runs/reader-comparison')/(prefix+'-calibration-'+e)/'lock.json'
        lock=json.loads(lp.read_text())
        for path,sha in lock['source_hashes'].items():
            if digest(path)!=sha:raise ValueError('Calibration source changed')
    jobs=preflight['jobs']
    keys = [fingerprint(payload(candidate, j['system'], j['evidence'])) for j in jobs]
    maximum = sum(math.ceil(reservation(candidate, payload(candidate, j['system'], j['evidence']))*1e6) for j in jobs)
    plan = {'scope': 'Fixed588 held-out summaries across four locked endpoints. Exact original Flex summarizer execution, no judgment requests or test outcome access. No retries/fallback. Check every response before next dispatch.',
            'reader': execution_manifest(candidate), 'jobs': jobs,
            'request_allowlist': keys, 'maximum_reserved_microusd': maximum,
            'preflight_sha256':digest(preflight_path),
            'code_sha256': digest(__file__)}
    if len(set(keys)) != 588:
        raise ValueError('Expected588 distinct requests')
    if a.dry_run:
        print(json.dumps({'maximum_reserved_microusd': maximum, 'requests': len(jobs)}))
        return
    if a.out.exists():
        raise ValueError('Preserve prior attempt')
    with file_lock(str(a.budget_file)+'.lock'):
        b = json.loads(a.budget_file.read_text())
        if not b['status'].startswith('paused') or b['additional_limit_usd'] != 40:
            raise ValueError('Paused authorized40 budget required')
        if b['reserved_microusd'] != sum(r['reserved_microusd'] for r in b['records'].values() if r['status']=='reserved'):
            raise ValueError('Unknown reservations changed')
        if any(r['request_sha256'] in keys for r in b['records'].values()):
            raise ValueError('No retries')
        if maximum > 40_000_000-b['spent_microusd']-b['reserved_microusd']:
            raise ValueError('Whole qualification must fit current allowance')
        a.out.mkdir(parents=True)
        write_json(a.out/'registration.json', plan)
        b.update(status='active',active_request_allowlist=keys,
                 active_audit_manifest_sha256=fingerprint(plan),audit_scope=plan['scope'])
        write_json(a.budget_file,b)
    sources={}
    try:
        for i,j in enumerate(jobs):
            jp=a.out/f'job-{i}.json';write_json(jp,{'jobs':[j]})
            run_jobs(candidate,jp,a.out/'reader',a.credential_file,a.budget_file)
            result=json.loads((a.out/'reader/results'/(j['request_id']+'.json')).read_text())
            if result.get('status') != 'ok':
                raise ValueError('Unavailable summary; preserve result and stop for diagnosis')
            from verify_accepted_summary_receipts import verify_one
            rawpaths=list((a.out/'reader/api-cache').glob(result['api_request_sha256']+'-raw-*.json'))
            if len(rawpaths)!=1:raise ValueError('Expected unique raw receipt')
            raw=json.loads(rawpaths[0].read_text());ledger=json.loads(a.budget_file.read_text())
            verify_one(j,result,raw,ledger['records'][raw['budget_reservation']],candidate,'lowreference')
            for path in [rawpaths[0],a.out/'reader/results'/(j['request_id']+'.json')]:sources[str(path)]=digest(path)
        write_json(a.out/'complete.json',{'requests':588,'source_hashes':sources,'scope':'Receipt-verified held-out summaries only. Collection, two-judge review and frozen-threshold evaluation remain required.'})
    finally:
        b=pause_budget(a.budget_file)
        write_json(a.out/'cost.json',{k:b.get(k) for k in ['status','spent_microusd','reserved_microusd','additional_limit_usd']})


if __name__=='__main__':
    main()
