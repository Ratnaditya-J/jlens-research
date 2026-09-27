"""Separate standard-route qualification; no mixing with accepted Flex outputs."""
import argparse
import json
import math
from pathlib import Path
from audit_budgeted_reader import fixture_jobs, pause_budget
from budgeted_api_client import file_lock
from budgeted_hosted_standardreference import payload, reservation
from hosted_text_reader_standardreference import execution_manifest, run_jobs
from contracts import fingerprint
from smoke import digest, write_json


def main():
    p = argparse.ArgumentParser()
    for n in ['budget-file', 'credential-file', 'out']:
        p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    candidate = 'gpt54standardreference'
    groups = [('bridge', Path('runs/local-reader-bridge'), 48),
              ('policy', Path('runs/local-policy-reader-check'), 24)]
    jobs = [j for _, path, n in groups for j in fixture_jobs(path, n)]
    keys = [fingerprint(payload(candidate, j['system'], j['evidence'])) for j in jobs]
    maximum = sum(math.ceil(reservation(candidate, payload(candidate, j['system'], j['evidence']))*1e6) for j in jobs)
    plan = {'scope': 'Separate standard OpenAI route qualification of same GPT-5.4 low-reasoning settings. Same48 bridge and24 policy fixtures and unchanged gates. No production, held-out inference or claim of route equivalence. No retries/fallback. Check every response before next dispatch.',
            'reader': execution_manifest(candidate), 'jobs': jobs,
            'request_allowlist': keys, 'maximum_reserved_microusd': maximum,
            'protocol_hashes': {name: digest(path/'protocol.json') for name,path,_ in groups},
            'code_sha256': digest(__file__)}
    if len(set(keys)) != 72:
        raise ValueError('Expected72 distinct requests')
    if a.dry_run:
        print(json.dumps({'maximum_reserved_microusd': maximum, 'requests': len(jobs)}))
        return
    if a.out.exists():
        raise ValueError('Preserve prior attempt')
    with file_lock(str(a.budget_file)+'.lock'):
        b = json.loads(a.budget_file.read_text())
        if not b['status'].startswith('paused') or b['additional_limit_usd'] != 20:
            raise ValueError('Paused authorized20 budget required')
        if b['reserved_microusd'] != sum(r['reserved_microusd'] for r in b['records'].values() if r['status']=='reserved'):
            raise ValueError('Unknown reservations changed')
        if any(r['request_sha256'] in keys for r in b['records'].values()):
            raise ValueError('No retries')
        if maximum > 20_000_000-b['spent_microusd']-b['reserved_microusd']:
            raise ValueError('Whole qualification must fit current allowance')
        a.out.mkdir(parents=True)
        write_json(a.out/'registration.json', plan)
        b.update(status='active',active_request_allowlist=keys,
                 active_audit_manifest_sha256=fingerprint(plan),audit_scope=plan['scope'])
        write_json(a.budget_file,b)
    try:
        for i,j in enumerate(jobs):
            jp=a.out/f'job-{i}.json';write_json(jp,{'jobs':[j]})
            run_jobs(candidate,jp,a.out/'reader',a.credential_file,a.budget_file)
            result=json.loads((a.out/'reader/results'/(j['request_id']+'.json')).read_text())
            if result.get('status') != 'ok':
                raise ValueError('Unavailable qualification response; no further dispatch')
        write_json(a.out/'complete.json',{'requests':72,'scope':'Transport completion only; unchanged bridge/policy evaluation and coverage gates remain required.'})
    finally:
        b=pause_budget(a.budget_file)
        write_json(a.out/'cost.json',{k:b.get(k) for k in ['status','spent_microusd','reserved_microusd','additional_limit_usd']})


if __name__=='__main__':
    main()
