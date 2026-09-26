"""Pinned-route hosted text reader; the shared budget allowlist gates every call."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from budgeted_hosted_reference import CONFIGS, request_json
LOW_COST_CANDIDATES = CONFIGS
from contracts import fingerprint
from smoke import digest, write_json


def execution_manifest(candidate):
    root = Path(__file__).parent
    return {'kind': 'bounded-hosted-reference-reader-v1', 'model': LOW_COST_CANDIDATES[candidate],
            'max_new_tokens': 1600, 'temperature': 0, 'reasoning': 'unsupported-omitted',
            'response_format': 'json_object', 'workers': 1, 'http_failure_policy': 'pause_entire_audit_on_first_http_error', 'allow_fallbacks': False,
            'evidence_encoding': 'json-literal-delimiters-v1',
            'code_sha256': digest(__file__),
            'transport_code_sha256': digest(root/'budgeted_hosted_reference.py'),
            'budget_guard_code_sha256': digest(root/'budgeted_api_client.py'),
            'evidence_encoder_code_sha256': digest(root/'literal_evidence.py'),
            'decoder_code_sha256': digest(root/'contracts.py'),
            'scope': 'Text evidence only. No subject states, outcome labels, probe scores or other judge judgments. Hosted weights cannot be hash-pinned; exact provider responses are retained. Request allowlist and budget must be separately authorized for each batch.'}


def run_jobs(candidate, jobs_path, out, credential_file, budget_file):
    jobs = json.loads(jobs_path.read_text())['jobs']
    if len({j['request_id'] for j in jobs}) != len(jobs):
        raise ValueError('Duplicate request IDs')
    for job in jobs:
        if set(job) != {'request_id', 'system', 'evidence'} or job['request_id'] != fingerprint({'system': job['system'], 'evidence': job['evidence']}):
            raise ValueError('Changed or unblinded request payload')
    manifest = execution_manifest(candidate)
    out.mkdir(parents=True, exist_ok=True)
    (out/'results').mkdir(exist_ok=True)
    mp = out/'manifest.json'
    if mp.exists() and json.loads(mp.read_text()) != manifest:
        raise ValueError('Reader execution differs from existing outputs')
    write_json(mp, manifest)
    sha = fingerprint(manifest)

    def run(job):
        path = out/'results'/(job['request_id']+'.json')
        if path.exists():
            prior = json.loads(path.read_text())
            if prior['request_id'] != job['request_id'] or prior['manifest_sha256'] != sha:
                raise ValueError('Existing result identity differs')
            return prior
        result = {'request_id': job['request_id'], 'manifest_sha256': sha}
        try:
            reply = request_json(candidate, job['system'], job['evidence'],
                                        out/'api-cache', credential_file, budget_file=budget_file)
            result.update(status='ok', judgment=reply['judgment'], raw_response=reply['raw_response'],
                          api_request_sha256=reply['request_sha256'])
        except Exception as exc:
            # Do not print exception bodies: HTTP errors could include credentials.
            # Raw API replies and uncertain reservations remain in their ledgers.
            result.update(status='unavailable', error_type=type(exc).__name__)
        write_json(path, result)
        return result

    with ThreadPoolExecutor(max_workers=1) as pool:
        results = list(pool.map(run, jobs))
    write_json(out/(jobs_path.stem+'-complete.json'),
               {'jobs_sha256': digest(jobs_path), 'manifest_sha256': sha, 'unique_requests': len(jobs)})
    print(json.dumps({'candidate': candidate, 'jobs': jobs_path.name, 'n': len(results),
                      'valid_transport_results': sum(r['status'] == 'ok' for r in results)}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', choices=sorted(LOW_COST_CANDIDATES), required=True)
    for name in ['jobs', 'out', 'credential-file', 'budget-file']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    run_jobs(a.candidate, a.jobs, a.out, a.credential_file, a.budget_file)


if __name__ == '__main__':
    main()
