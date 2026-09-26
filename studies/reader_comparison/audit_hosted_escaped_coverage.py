"""The fixed 90-request validation coverage pilot, only for qualified readers."""
import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from audit_budgeted_reader import pause_budget
from budgeted_api_client import file_lock, lowcost_payload, lowcost_reservation
from budgeted_hosted_medium import payload as medium_payload
from collect_local_readers import execution_source
from contracts import fingerprint
from evaluate_local_bridge import evaluate
from hosted_text_reader import execution_manifest as pair_manifest, run_jobs as run_pair
from hosted_text_reader_medium import execution_manifest as medium_manifest, run_jobs as run_medium
from smoke import digest, write_json
from validate_reader_gates import ready


from audit_hosted_coverage import activate_coverage_budget, verify_qualification
from budgeted_hosted_escaped import payload, reservation
from hosted_text_reader_escaped import execution_manifest, run_jobs


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', choices=['deepseek32escaped'], required=True)
    for name in ['reader', 'gates', 'bridge', 'policy', 'pilot', 'credential-file', 'budget-file', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    expected = execution_manifest(a.candidate)
    sources = verify_qualification(a.reader, a.gates, a.bridge, a.policy, expected)
    pm = json.loads((a.pilot/'manifest.json').read_text())
    if pm['phase'] != 'validation' or pm['stage'] != 'coverage-pilot' or digest(a.pilot/'jobs.json') != pm['jobs_sha256']:
        raise ValueError('Only the registered validation coverage pilot is allowed')
    for path, sha in pm['source_hashes'].items():
        if digest(path) != sha:
            raise ValueError('Coverage pilot source changed')
    jobs = json.loads((a.pilot/'jobs.json').read_text())['jobs']
    payloads = [payload(j['system'], j['evidence']) for j in jobs]
    keys = sorted(fingerprint(request) for request in payloads)
    if len(keys) != 90 or len(set(keys)) != 90:
        raise ValueError('Unexpected coverage cohort')
    plan = {'kind': 'bounded-hosted-escaped-coverage-v1', 'reader': expected,
            'request_allowlist': keys,
            'maximum_reserved_microusd': sum(math.ceil(reservation(request)*1e6) for request in payloads),
            'pilot_manifest_sha256': digest(a.pilot/'manifest.json'), 'jobs_sha256': digest(a.pilot/'jobs.json'),
            'qualification_source_hashes': sources, 'code_sha256': digest(__file__),
            'qualification_guard_code_sha256': digest(Path(__file__).with_name('audit_hosted_coverage.py')),
            'execution_verifier_code_sha256': digest(Path(__file__).with_name('collect_local_readers.py')),
            'scope': '90 fixed validation engineering-coverage requests only. Existing cumulative $1 cap unchanged. No retries, production or held-out inference.'}
    if a.dry_run:
        print(json.dumps(plan, indent=2))
        return
    if a.out.exists():
        raise ValueError('Preserve prior coverage run; no automatic retry')
    a.out.mkdir(parents=True)
    write_json(a.out/'audit-plan.json', plan)
    jobs_path = a.out/'reader-coverage-pilot-jobs.json'
    shutil.copyfile(a.pilot/'jobs.json', jobs_path)
    activate_coverage_budget(a.budget_file, plan)
    try:
        with file_lock(str(a.budget_file)+'.lock'):
            ledger = json.loads(a.budget_file.read_text())
            if ledger['active_audit_manifest_sha256'] != fingerprint(plan):
                raise ValueError('Active audit identity changed')
            ledger['audit_scope'] = plan['scope']
            write_json(a.budget_file, ledger)
        run_jobs(a.candidate, jobs_path, a.out/'reader', a.credential_file, a.budget_file)
    finally:
        ledger = pause_budget(a.budget_file)
        write_json(a.out/'cost.json', {'cumulative_limit_usd': ledger['additional_limit_usd'],
                   'cumulative_spent_usd': ledger.get('spent_microusd', 0)/1e6,
                   'reserved_uncertain_usd': ledger.get('reserved_microusd', 0)/1e6,
                   'ledger_status': ledger['status'], 'ledger_sha256': digest(a.budget_file)})
    subprocess.run([sys.executable, str(Path(__file__).with_name('evaluate_reader_coverage.py')),
                    '--pilot', str(a.pilot), '--reader', str(a.out/'reader'),
                    '--out', str(a.out/'coverage.json')], check=True)


if __name__ == '__main__':
    main()
