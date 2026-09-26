"""One 72-request GPT-5.4 nano qualification; never raises the shared $1 cap."""
import argparse
import json
import math
import shutil
from pathlib import Path

from audit_budgeted_reader import fixture_jobs, pause_budget
from audit_hosted_coverage import activate_coverage_budget as activate_budget
from budgeted_api_client import file_lock, lowcost_reservation
from budgeted_hosted_nano import payload
from contracts import fingerprint
from hosted_text_reader_nano import execution_manifest, run_jobs
from smoke import digest, write_json


def main():
    p = argparse.ArgumentParser()
    for name in ['bridge', 'policy', 'credential-file', 'budget-file', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    groups = [('bridge', a.bridge, fixture_jobs(a.bridge, 48), 'local-bridge-jobs'),
              ('policy', a.policy, fixture_jobs(a.policy, 24), 'local-policy-check-jobs')]
    requests = [payload(j['system'], j['evidence']) for _, _, jobs, _ in groups for j in jobs]
    keys = sorted(fingerprint(request) for request in requests)
    maximum = sum(math.ceil(lowcost_reservation(request)*1e6) for request in requests)
    registered_path = Path(__file__).parent/'evidence/hosted-gpt54nano-prepared-plan.json'
    registered = json.loads(registered_path.read_text())
    if len(keys) != 72 or len(set(keys)) != 72 or keys != registered['request_allowlist'] or maximum != registered['maximum_reserved_microusd']:
        raise ValueError('Medium audit differs from preregistered exact requests or maximum reservation')
    plan = {'kind': 'bounded-hosted-gpt54nano-qualification-v1',
            'reader': execution_manifest('gpt54nano'),
            'fixture_protocol_sha256': {n: digest(d/'protocol.json') for n, d, _, _ in groups},
            'request_allowlist': keys, 'maximum_reserved_microusd': maximum,
            'code_sha256': digest(__file__), 'prepared_plan_sha256': digest(registered_path),
            'fixture_loader_code_sha256': digest(Path(__file__).with_name('audit_budgeted_reader.py')),
            'activation_guard_code_sha256': digest(Path(__file__).with_name('audit_hosted_coverage.py')),
            'scope': '72 fixed qualification requests only, under existing cumulative $1 ceiling. No retry, production or held-out inference. Distinct GPT-5.4 nano candidate after GPT-OSS failures. Prior uncertain reservations are fully retained.'}
    if a.dry_run:
        print(json.dumps(plan, indent=2))
        return
    if a.out.exists():
        raise ValueError('Preserve prior medium audit; no automatic rerun')
    a.out.mkdir(parents=True)
    write_json(a.out/'audit-plan.json', plan)
    inputs = a.out/'inputs'
    inputs.mkdir()
    for _, directory, _, stem in groups:
        shutil.copyfile(directory/'jobs.json', inputs/(stem+'.json'))
    activate_budget(a.budget_file, plan)
    try:
        # Reuse the tested ceiling/reservation guard; replace its pair-specific
        # scope text before any request is dispatched by this coordinator.
        with file_lock(str(a.budget_file)+'.lock'):
            ledger = json.loads(a.budget_file.read_text())
            if ledger['active_audit_manifest_sha256'] != fingerprint(plan):
                raise ValueError('Active audit identity changed')
            ledger['audit_scope'] = plan['scope']
            write_json(a.budget_file, ledger)
        for _, _, _, stem in groups:
            run_jobs('gpt54nano', inputs/(stem+'.json'), a.out/'reader', a.credential_file, a.budget_file)
    finally:
        ledger = pause_budget(a.budget_file)
        write_json(a.out/'cost.json', {'cumulative_limit_usd': ledger['additional_limit_usd'],
                   'cumulative_spent_usd': ledger.get('spent_microusd', 0)/1e6,
                   'reserved_uncertain_usd': ledger.get('reserved_microusd', 0)/1e6,
                   'ledger_status': ledger['status'], 'ledger_sha256': digest(a.budget_file)})


if __name__ == '__main__':
    main()
