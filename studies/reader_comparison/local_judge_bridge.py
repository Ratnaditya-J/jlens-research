"""Build a blinded validation-only reader bridge from existing cached judgments."""
import argparse
import json
from pathlib import Path
from contracts import fingerprint
from smoke import digest, write_json


def build(scores, cache, per_score=16):
    candidates = {score: {} for score in range(3)}
    for episode in scores:
        for arm, value in episode.items():
            if not isinstance(value, dict) or not value.get('agreement'):
                continue
            reviewers = value.get('reviewer_scores', [])
            if len(reviewers) != 2 or reviewers[0] != reviewers[1]:
                continue
            score = reviewers[0]
            if type(score) is not int or score not in candidates:
                raise ValueError('Invalid reference score')
            requests = []
            for sha in value['request_sha256']:
                files = sorted(cache.glob(sha + '-raw-*.json'))
                if not files:
                    raise ValueError('Missing cached request ' + sha)
                requests.append(json.loads(files[0].read_text())['request'])
            if len(requests) != 2 or requests[0]['messages'] != requests[1]['messages']:
                raise ValueError('Reference reviewers received different evidence')
            if {r['model'] for r in requests} != {'openai/gpt-4.1', 'openai/gpt-5.4'}:
                raise ValueError('Unexpected reference reviewer identity')
            messages = requests[0]['messages']
            if [m['role'] for m in messages] != ['system', 'user']:
                raise ValueError('Unexpected message contract')
            payload = {'system': messages[0]['content'], 'evidence': json.loads(messages[1]['content'])}
            request_id = fingerprint(payload)
            candidates[score][request_id] = (
                {'request_id': request_id, **payload},
                {'request_id': request_id, 'reference_score': score,
                 'episode_id': episode['episode_id'], 'arm': arm,
                 'cached_request_sha256': value['request_sha256']})
    jobs, references = [], []
    seen = set()
    for score in range(3):
        if len(candidates[score]) < per_score:
            raise ValueError('Insufficient unique reference requests for score ' + str(score))
        for request_id in sorted(candidates[score])[:per_score]:
            if request_id in seen:
                raise ValueError('Conflicting reference scores for identical evidence')
            seen.add(request_id)
            job, reference = candidates[score][request_id]
            jobs.append(job)
            references.append(reference)
    return sorted(jobs, key=lambda j: j['request_id']), references


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scores', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.scores.parent.name != 'fresh-offset32-jsummary-validation':
        raise ValueError('Bridge must use the registered validation-only source')
    jobs, references = build(json.loads(a.scores.read_text()), a.cache)
    a.out.mkdir(parents=True, exist_ok=True)
    write_json(a.out/'jobs.json', {'jobs': jobs})
    write_json(a.out/'references.json', {'references': references})
    write_json(a.out/'protocol.json', {
        'protocol': 'local-reader-bridge-v1', 'source_scores_sha256': digest(a.scores),
        'jobs_sha256': digest(a.out/'jobs.json'), 'references_sha256': digest(a.out/'references.json'),
        'selection': '16 unique requests per consensus score, ascending content hash; validation only',
        'valid_json_fraction_min': 0.90, 'exact_reference_agreement_fraction_min': 0.80,
        'denominator': 'All 48 requests, including unavailable outputs as failures',
        'scope': 'Premium reviewer consensus is a proxy, not ground truth; this bridge does not establish Qwen-domain validity.',
        'isolation': 'Upload jobs only. Reference labels and source episode metadata remain local.',
        'failure_policy': 'No held-out judging before the gate passes. A predeclared 512-to-1024 output-token retry is allowed only for truncation; preserve both attempts. Other changes require a new registered protocol.'})
    print(json.dumps({'jobs': len(jobs), 'out': str(a.out)}))


if __name__ == '__main__':
    main()
