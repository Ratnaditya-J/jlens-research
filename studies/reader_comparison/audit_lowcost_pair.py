"""One 144-request qualification audit under the existing shared $1 ceiling."""
import argparse
import json
import math
import shutil
import time
from pathlib import Path

from audit_budgeted_reader import fixture_jobs, pause_budget
from budgeted_api_client import file_lock, lowcost_payload, lowcost_reservation
from contracts import fingerprint
from hosted_text_reader import execution_manifest, run_jobs
from smoke import digest, write_json


def activate_budget(path, plan):
    with file_lock(str(path)+'.lock'):
        ledger = json.loads(path.read_text())
        if not ledger['status'].startswith('paused') or ledger.get('reserved_microusd', 0):
            raise ValueError('Require paused ledger without uncertain reservations')
        if not 0 < ledger['additional_limit_usd'] <= 1:
            raise ValueError('This audit cannot raise the existing $1 ceiling')
        if any(r['request_sha256'] in plan['request_allowlist'] for r in ledger['records'].values()):
            raise ValueError('Candidate request already attempted; preserve prior audit')
        available = math.floor(ledger['additional_limit_usd']*1e6)-ledger.get('spent_microusd', 0)
        if plan['maximum_reserved_microusd'] > available:
            raise ValueError('All planned reservations must fit the remaining budget')
        ledger.update(status='active', active_request_allowlist=plan['request_allowlist'],
                      active_audit_manifest_sha256=fingerprint(plan),
                      audit_scope='144 fixed qualification requests only; existing $1 cumulative amendment cap unchanged; no retries, no production/test requests')
        write_json(path, ledger)


def main():
    p = argparse.ArgumentParser()
    for name in ['bridge', 'policy', 'credential-file', 'budget-file', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    groups = [('bridge', a.bridge, fixture_jobs(a.bridge, 48), 'local-bridge-jobs'),
              ('policy', a.policy, fixture_jobs(a.policy, 24), 'local-policy-check-jobs')]
    candidates = ['gptoss120', 'deepseek32']
    payloads = [lowcost_payload(c, j['system'], j['evidence'])
                for c in candidates for _, _, jobs, _ in groups for j in jobs]
    keys = [fingerprint(p) for p in payloads]
    if len(keys) != 144 or len(set(keys)) != 144:
        raise ValueError('Unexpected qualification cohort or duplicate API request')
    plan = {'kind': 'bounded-hosted-pair-qualification-v1',
            'readers': {c: execution_manifest(c) for c in candidates},
            'fixture_protocol_sha256': {n: digest(d/'protocol.json') for n, d, _, _ in groups},
            'request_allowlist': sorted(keys),
            'maximum_reserved_microusd': sum(math.ceil(lowcost_reservation(p)*1e6) for p in payloads),
            'code_sha256': digest(__file__),
            'fixture_loader_code_sha256': digest(Path(__file__).with_name('audit_budgeted_reader.py')),
            'scope': 'Two adaptive qualification candidates after failed local executions; same 48+24 fixtures and original gates. No held-out inference. No automatic budget increase, retry or production adoption.'}
    if a.dry_run:
        print(json.dumps(plan, indent=2))
        return
    if a.out.exists():
        raise ValueError('Preserve existing audit directory; no automatic rerun')
    a.out.mkdir(parents=True)
    write_json(a.out/'audit-plan.json', plan)
    inputs = a.out/'inputs'
    inputs.mkdir()
    for _, directory, _, stem in groups:
        shutil.copyfile(directory/'jobs.json', inputs/(stem+'.json'))
    activate_budget(a.budget_file, plan)
    try:
        for candidate in candidates:
            for _, _, _, stem in groups:
                run_jobs(candidate, inputs/(stem+'.json'), a.out/candidate,
                         a.credential_file, a.budget_file)
    finally:
        ledger = pause_budget(a.budget_file)
        write_json(a.out/'cost.json', {'cumulative_limit_usd': ledger['additional_limit_usd'],
                   'cumulative_spent_usd': ledger.get('spent_microusd', 0)/1e6,
                   'reserved_uncertain_usd': ledger.get('reserved_microusd', 0)/1e6,
                   'ledger_status': ledger['status'], 'ledger_sha256': digest(a.budget_file),
                   'ended_at': time.time()})


if __name__ == '__main__':
    main()
