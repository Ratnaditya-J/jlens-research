"""The fixed 90-request validation coverage pilot, only for qualified readers."""
import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from audit_budgeted_reader import pause_budget
from budgeted_api_client import file_lock
from contracts import fingerprint
from smoke import digest, write_json
from audit_hosted_coverage import verify_qualification
from audit_reader_coverage_phase import activate_coverage_budget
import budgeted_hosted_direct
import budgeted_hosted_reference
import hosted_text_reader_direct
import hosted_text_reader_reference
import hosted_text_reader_lowreference
import budgeted_hosted_lowreference

CANDIDATES = {
    'gpt54lowreference': (budgeted_hosted_lowreference, hosted_text_reader_lowreference),
    'deepseek32direct': (budgeted_hosted_direct, hosted_text_reader_direct),
    'gpt41reference': (budgeted_hosted_reference, hosted_text_reader_reference),
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', choices=sorted(CANDIDATES), required=True)
    for name in ['reader', 'gates', 'bridge', 'policy', 'pilot', 'credential-file', 'budget-file', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    transport, runner = CANDIDATES[a.candidate]
    expected = runner.execution_manifest(a.candidate)
    sources = verify_qualification(a.reader, a.gates, a.bridge, a.policy, expected)
    pm = json.loads((a.pilot/'manifest.json').read_text())
    if pm['phase'] != 'validation' or pm['stage'] != 'coverage-pilot' or digest(a.pilot/'jobs.json') != pm['jobs_sha256']:
        raise ValueError('Only the registered validation coverage pilot is allowed')
    for path, sha in pm['source_hashes'].items():
        if digest(path) != sha:
            raise ValueError('Coverage pilot source changed')
    if pm['jobs_sha256'] != 'ca9bc458bfc298a2c649c5de0e4bd0288fbe85c78de6a63f13bd88cbf7d8c441':
        raise ValueError('Coverage cohort differs from preregistered90 requests')
    jobs = json.loads((a.pilot/'jobs.json').read_text())['jobs']
    payloads = [transport.payload(a.candidate, j['system'], j['evidence']) for j in jobs]
    keys = sorted(fingerprint(request) for request in payloads)
    if len(keys) != 90 or len(set(keys)) != 90:
        raise ValueError('Unexpected coverage cohort')
    plan = {'kind': 'bounded-hosted-registered-reader-coverage-v1', 'reader': expected,
            'request_allowlist': keys,
            'maximum_reserved_microusd': sum(math.ceil(transport.reservation(a.candidate, request)*1e6) for request in payloads),
            'pilot_manifest_sha256': digest(a.pilot/'manifest.json'), 'jobs_sha256': digest(a.pilot/'jobs.json'),
            'qualification_source_hashes': sources, 'code_sha256': digest(__file__),
            'activation_guard_sha256': digest(Path(__file__).with_name('audit_reader_coverage_phase.py')),
            'qualification_guard_code_sha256': digest(Path(__file__).with_name('audit_hosted_coverage.py')),
            'execution_verifier_code_sha256': digest(Path(__file__).with_name('collect_local_readers.py')),
            'scope': '90 fixed validation engineering-coverage requests only. Existing cumulative $5 cap unchanged. No retries, production or held-out inference.'}
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
        runner.run_jobs(a.candidate, jobs_path, a.out/'reader', a.credential_file, a.budget_file)
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
