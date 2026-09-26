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


def activate_coverage_budget(path, plan):
    """Keep prior uncertain charges fully reserved; never retry their requests."""
    with file_lock(str(path)+'.lock'):
        ledger = json.loads(path.read_text())
        if not ledger['status'].startswith('paused'):
            raise ValueError('Previous coordinator must be finished and ledger paused')
        if not 0 < ledger['additional_limit_usd'] <= 1:
            raise ValueError('Coverage cannot raise the existing $1 ceiling')
        if any(record['request_sha256'] in plan['request_allowlist'] for record in ledger['records'].values()):
            raise ValueError('Coverage request already attempted; no retry')
        held = ledger.get('reserved_microusd', 0)
        if held != sum(record['reserved_microusd'] for record in ledger['records'].values() if record['status'] == 'reserved'):
            raise ValueError('Uncertain reservation ledger is inconsistent')
        remaining = math.floor(ledger['additional_limit_usd']*1e6)-ledger.get('spent_microusd', 0)-held
        if plan['maximum_reserved_microusd'] > remaining:
            raise ValueError('All coverage reservations must fit after carrying prior uncertain charges')
        ledger.update(status='active', active_request_allowlist=plan['request_allowlist'],
                      active_audit_manifest_sha256=fingerprint(plan), audit_scope=plan['scope'],
                      carried_uncertain_microusd_at_activation=held)
        write_json(path, ledger)


def verify_qualification(reader, gates, bridge, policy, expected):
    manifest = json.loads((reader/'manifest.json').read_text())
    if manifest != expected:
        raise ValueError('Qualification execution differs from proposed coverage execution')
    execution_source(manifest)
    complete = json.loads((gates/'complete.json').read_text())
    if not complete['passed'] or complete['reader_manifest_sha256'] != digest(reader/'manifest.json'):
        raise ValueError('Both fixed qualification gates must pass')
    sources = [reader/'manifest.json', gates/'complete.json']
    for name, fixtures, completion in [('bridge', bridge, 'local-bridge-jobs-complete.json'),
                                      ('policy', policy, 'local-policy-check-jobs-complete.json')]:
        if not ready(reader, fixtures, completion):
            raise ValueError('Qualification outputs are incomplete')
        protocol = json.loads((fixtures/'protocol.json').read_text())
        for artifact in ['jobs', 'references']:
            if digest(fixtures/(artifact+'.json')) != protocol[artifact+'_sha256']:
                raise ValueError('Qualification fixture changed')
        path = gates/(name+'.json')
        report = json.loads(path.read_text())
        if (digest(path) != complete['reports_sha256'][name] or not report['passed']
                or report['manifest_sha256'] != fingerprint(manifest)
                or report['protocol_sha256'] != digest(fixtures/'protocol.json')):
            raise ValueError('Qualification report provenance differs')
        references = json.loads((fixtures/'references.json').read_text())['references']
        results = {ref['request_id']: json.loads((reader/'results'/(ref['request_id']+'.json')).read_text())
                   for ref in references}
        actual = evaluate(references, results, fingerprint(manifest))
        if (actual['valid_fraction'] < protocol['valid_json_fraction_min'] or
                actual['exact_agreement_fraction'] < protocol['exact_reference_agreement_fraction_min']):
            raise ValueError('Raw qualification judgments fail the fixed gate')
        for score, minimum in protocol.get('minimum_score_recall', {}).items():
            subset = [row for row in actual['rows'] if row['reference_score'] == int(score)]
            if not subset or sum(row['exact_agreement'] for row in subset)/len(subset) < minimum:
                raise ValueError('Raw qualification judgments fail a class gate')
        sources.extend([fixtures/'protocol.json', fixtures/'jobs.json', fixtures/'references.json', path, reader/completion])
        sources.extend(reader/'results'/(ref['request_id']+'.json') for ref in references)
    return {str(path.resolve()): digest(path) for path in sources}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', choices=['deepseek32', 'gptoss20medium'], required=True)
    for name in ['reader', 'gates', 'bridge', 'policy', 'pilot', 'credential-file', 'budget-file', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    medium = a.candidate == 'gptoss20medium'
    expected = medium_manifest(a.candidate) if medium else pair_manifest(a.candidate)
    sources = verify_qualification(a.reader, a.gates, a.bridge, a.policy, expected)
    pm = json.loads((a.pilot/'manifest.json').read_text())
    if pm['phase'] != 'validation' or pm['stage'] != 'coverage-pilot' or digest(a.pilot/'jobs.json') != pm['jobs_sha256']:
        raise ValueError('Only the registered validation coverage pilot is allowed')
    for path, sha in pm['source_hashes'].items():
        if digest(path) != sha:
            raise ValueError('Coverage pilot source changed')
    jobs = json.loads((a.pilot/'jobs.json').read_text())['jobs']
    payloads = [(medium_payload(j['system'], j['evidence']) if medium else
                 lowcost_payload(a.candidate, j['system'], j['evidence'])) for j in jobs]
    keys = sorted(fingerprint(request) for request in payloads)
    if len(keys) != 90 or len(set(keys)) != 90:
        raise ValueError('Unexpected coverage cohort')
    plan = {'kind': 'bounded-hosted-coverage-v1', 'reader': expected,
            'request_allowlist': keys,
            'maximum_reserved_microusd': sum(math.ceil(lowcost_reservation(request)*1e6) for request in payloads),
            'pilot_manifest_sha256': digest(a.pilot/'manifest.json'), 'jobs_sha256': digest(a.pilot/'jobs.json'),
            'qualification_source_hashes': sources, 'code_sha256': digest(__file__),
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
        (run_medium if medium else run_pair)(a.candidate, jobs_path, a.out/'reader', a.credential_file, a.budget_file)
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
