"""One 72-request GPT-5.4 low-reasoning reference-family qualification; unchanged audit allocation within the existing $10 ceiling."""
import argparse
import json
import math
import shutil
from pathlib import Path

from audit_budgeted_reader import fixture_jobs, pause_budget
from audit_lowreference_phase import activate_lowreference_phase as activate_budget
from budgeted_api_client import file_lock
from budgeted_hosted_lowreference import payload, reservation
from contracts import fingerprint
from hosted_text_reader_lowreference import execution_manifest, run_jobs
from smoke import digest, write_json


def main():
    p = argparse.ArgumentParser()
    for name in ['bridge', 'policy', 'credential-file', 'budget-file', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    groups = [('bridge', a.bridge, fixture_jobs(a.bridge, 48), 'local-bridge-jobs'),
              ('policy', a.policy, fixture_jobs(a.policy, 24), 'local-policy-check-jobs')]
    requests = [payload('gpt54lowreference', j['system'], j['evidence']) for _, _, jobs, _ in groups for j in jobs]
    keys = sorted(fingerprint(request) for request in requests)
    maximum = sum(math.ceil(reservation('gpt54lowreference',request)*1e6) for request in requests)
    registered_path = Path(__file__).parent/'evidence/hosted-gpt54lowreference-prepared-plan.json'
    registered = json.loads(registered_path.read_text())
    if len(keys) != 72 or len(set(keys)) != 72 or keys != registered['request_allowlist'] or maximum != registered['maximum_reserved_microusd']:
        raise ValueError('Reference-family audit differs from preregistered exact requests or maximum reservation')
    plan = {'kind': 'bounded-hosted-gpt54lowreference-qualification-v1', 'cumulative_limit_usd': 5,
            'reader': execution_manifest('gpt54lowreference'),
            'fixture_protocol_sha256': {n: digest(d/'protocol.json') for n, d, _, _ in groups},
            'request_allowlist': keys, 'maximum_reserved_microusd': maximum,
            'code_sha256': digest(__file__), 'prepared_plan_sha256': digest(registered_path),
            'fixture_loader_code_sha256': digest(Path(__file__).with_name('audit_budgeted_reader.py')),
            'activation_guard_code_sha256': digest(Path(__file__).with_name('audit_lowreference_phase.py')),
            'scope': '72 fixed qualification requests only, under explicitly registered cumulative $5 audit allocation within the $10 project ceiling. No retry, production or held-out inference. Standalone GPT-5.4 low-reasoning reference-family candidate after failed cheaper candidates; GPT-5.4 low-reasoning helped create reference labels so bridge agreement measures compatibility, not independent accuracy; no claim that a second reader already qualifies. Prior uncertain reservations are fully retained. A potential GPT-4.1/GPT-5.4 pair shares vendor and bridge provenance and is not a cross-family replication; individual-reader held-out metrics and independent episode labels remain required.'}
    if a.dry_run:
        print(json.dumps(plan, indent=2))
        return
    if a.out.exists():
        raise ValueError('Preserve prior GPT-5.4 low-reasoning reference-family audit; no automatic rerun')
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
            run_jobs('gpt54lowreference', inputs/(stem+'.json'), a.out/'reader', a.credential_file, a.budget_file)
    finally:
        ledger = pause_budget(a.budget_file)
        write_json(a.out/'cost.json', {'cumulative_limit_usd': ledger['additional_limit_usd'],
                   'cumulative_spent_usd': ledger.get('spent_microusd', 0)/1e6,
                   'reserved_uncertain_usd': ledger.get('reserved_microusd', 0)/1e6,
                   'ledger_status': ledger['status'], 'ledger_sha256': digest(a.budget_file)})


if __name__ == '__main__':
    main()
