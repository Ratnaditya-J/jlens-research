"""One bounded Gemini validation audit; the shared ledger is re-paused on exit."""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from budgeted_api_client import file_lock, request_json
from contracts import fingerprint
from evaluate_local_bridge import evaluate
from smoke import digest, write_json


def fixture_jobs(directory, expected_n):
    protocol = json.loads((directory/'protocol.json').read_text())
    if digest(directory/'jobs.json') != protocol['jobs_sha256']:
        raise ValueError('Registered audit jobs changed')
    jobs = json.loads((directory/'jobs.json').read_text())['jobs']
    if len(jobs) != expected_n or len({j['request_id'] for j in jobs}) != expected_n:
        raise ValueError('Unexpected audit cohort')
    for job in jobs:
        if set(job) != {'request_id', 'system', 'evidence'} or job['request_id'] != fingerprint({'system': job['system'], 'evidence': job['evidence']}):
            raise ValueError('Audit payload contains unexpected fields or changed evidence')
    return jobs


def activate_budget(path, manifest_sha):
    with file_lock(str(path)+'.lock'):
        ledger = json.loads(path.read_text())
        if not ledger['status'].startswith('paused') or ledger.get('spent_microusd', 0) or ledger.get('reserved_microusd', 0) or ledger['records']:
            raise ValueError('This initial audit requires the previously unused, paused amendment ledger')
        ledger.update(status='active', additional_limit_usd=1.0, spent_microusd=0, reserved_microusd=0,
                      active_audit_manifest_sha256=manifest_sha,
                      audit_scope='72 fixed validation requests only; maximum $1 additional spending, no automatic retries')
        write_json(path, ledger)


def pause_budget(path):
    with file_lock(str(path)+'.lock'):
        ledger = json.loads(path.read_text())
        if ledger['status'] == 'active':
            ledger['status'] = 'paused_after_reader_audit'
        ledger['audit_ended_at'] = time.time()
        write_json(path, ledger)
    return ledger


def main():
    p = argparse.ArgumentParser()
    for name in ('bridge', 'policy', 'credential-file', 'budget-file', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    groups = [('bridge', a.bridge, fixture_jobs(a.bridge, 48), 'local-bridge-jobs'),
              ('policy', a.policy, fixture_jobs(a.policy, 24), 'local-policy-check-jobs')]
    if a.out.exists():
        raise ValueError('Preserve this candidate attempt; no automatic reruns')
    a.out.mkdir(parents=True)
    (a.out/'results').mkdir()
    manifest = {'kind': 'budgeted-api-reader-audit-v1', 'model': {'repo': 'google/gemini-3.8-flash', 'family': 'gemini'},
                'max_new_tokens': 1600, 'temperature': 0, 'response_format': 'json_object',
                'provider_max_price_per_million': {'prompt': 1, 'completion': 4}, 'workers': 4,
                'code_sha256': digest(__file__), 'transport_code_sha256': digest(Path(__file__).with_name('budgeted_api_client.py')),
                'fixture_protocol_sha256': {name: digest(directory/'protocol.json') for name, directory, _, _ in groups},
                'scope': 'Adaptive cheaper candidate following failed local-reader agreement checks. Exact same evidence, rubrics and frozen gates. Hosted model cannot be pinned by weight hash; actual responses/providers are retained. Validation only, no study test inference.'}
    write_json(a.out/'manifest.json', manifest)
    manifest_sha = fingerprint(manifest)
    def run(job):
        result = {'request_id': job['request_id'], 'manifest_sha256': manifest_sha}
        try:
            reply = request_json('google/gemini-3.8-flash', job['system'], job['evidence'], a.out/'api-cache',
                                 a.credential_file, budget_file=a.budget_file, max_tokens=1600)
            raw = reply['raw_response']
            result.update(api_request_sha256=reply['request_sha256'], raw_response=raw,
                          judgment=reply['judgment'], status='ok')
            if raw['choices'][0].get('finish_reason') != 'stop':
                result.update(status='unavailable', error='Non-stop finish reason', truncated=True)
        except Exception as exc:
            # Keep uncertain reservations held; never turn an API error into a negative judgment.
            result.update(status='unavailable', error_type=type(exc).__name__)
        write_json(a.out/'results'/(job['request_id']+'.json'), result)
        return result
    activate_budget(a.budget_file, manifest_sha)
    try:
        for name, directory, jobs, stem in groups:
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(run, jobs))
            write_json(a.out/(stem+'-complete.json'), {'jobs_sha256': digest(directory/'jobs.json'),
                       'manifest_sha256': manifest_sha, 'unique_requests': len(jobs)})
            print(json.dumps({'completed_audit_group': name, 'requests': len(results),
                              'valid_transport_results': sum(r['status'] == 'ok' for r in results)}), flush=True)
    finally:
        ledger = pause_budget(a.budget_file)
        write_json(a.out/'cost.json', {'limit_usd': ledger['additional_limit_usd'],
                                     'spent_usd': ledger.get('spent_microusd', 0)/1e6,
                                     'reserved_uncertain_usd': ledger.get('reserved_microusd', 0)/1e6,
                                     'ledger_status': ledger['status'], 'ledger_sha256': digest(a.budget_file)})


if __name__ == '__main__':
    main()
