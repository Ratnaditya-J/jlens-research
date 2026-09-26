"""Offline provenance audit; never prints held-out outcomes or calls an API."""
import argparse
import json
from pathlib import Path

from audit_production import audit
from contracts import fingerprint, parse_json_reply
from review_policy import RUBRIC
from simulator import action_from_response
from smoke import digest, write_json


def verify(episodes, bank_path, audits_path, reviews):
    bank = json.loads(bank_path.read_text())
    items = {item['id']: item for item in bank['items']}
    audit_rows = json.loads(audits_path.read_text())
    audit_by_id = {row['episode_id']: row for row in audit_rows}
    rows = json.loads((reviews/'policy-reviews.json').read_text())
    done = json.loads((reviews/'complete.json').read_text())
    if done['reviews_sha256'] != digest(reviews/'policy-reviews.json') or done['rubric_sha256'] != fingerprint(RUBRIC):
        raise ValueError('Policy review artifact or rubric changed')
    if len(audit_by_id) != len(audit_rows) or len({row['episode_id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate audit/review episode identity')
    if {row['episode_id'] for row in rows} != set(audit_by_id) or done['n_episodes'] != len(rows):
        raise ValueError('Audit/review cohort differs')
    models = ['openai/gpt-5.4', 'anthropic/claude-sonnet-4.6']
    absent = 0
    receipts = {}
    episode_sources = {}
    review_cache_sources = {}
    for row in rows:
        path = episodes/(row['episode_id']+'.json')
        ep = json.loads(path.read_text())
        episode_sources[row['episode_id']] = digest(path)
        stored = audit_by_id[row['episode_id']]
        expected = audit(ep, items[row['episode_id'].rsplit('--', 1)[0]])
        if any(stored.get(key) != value for key, value in expected.items()):
            raise ValueError('Stored simulator result differs from replay')
        if stored['bank_sha256'] != fingerprint(bank) or stored['simulator_sha256'] != digest(Path(__file__).with_name('audit_production.py')):
            raise ValueError('Simulator or task-bank provenance differs')
        if row['episode_sha256'] != fingerprint(ep) or stored['episode_sha256'] != fingerprint(ep):
            raise ValueError('Review belongs to another trajectory')
        if len(row['reviews']) != len(models):
            raise ValueError('Policy reviewer slot count differs')
        judgments = []
        for model, result in zip(models, row['reviews']):
            if result is None:
                absent += 1
                continue
            action, _, _ = action_from_response(ep['raw_response'])
            evidence = {'messages': ep['messages'], 'response': ep['raw_response'],
                        'parsed_action': action, 'truncated': ep['truncated']}
            payload = {'model': model, 'messages': [{'role': 'system', 'content': RUBRIC},
                       {'role': 'user', 'content': json.dumps(evidence, ensure_ascii=False)}],
                       'response_format': {'type': 'json_object'}, 'max_tokens': 1600,
                       'provider': {'require_parameters': True}}
            payload.update({'reasoning': {'effort': 'low'}} if model.startswith('openai/gpt-5') else {'temperature': 0})
            key = fingerprint(payload)
            if result['request_sha256'] != key or result['request'] != payload or result['requested_model'] != model or result['resolved_model'] != model:
                raise ValueError('Policy reviewer received a different or unblinded request')
            judgment = result['judgment']
            if (judgment.get('submitted_action') != action or
                    {key: type(value) for key, value in judgment.get('submitted_action', {}).items()} != {key: type(value) for key, value in action.items()} or
                    judgment.get('label') not in ['violation', 'benign', 'uncertain'] or
                    judgment.get('confidence') not in ['high', 'medium', 'low']):
                raise ValueError('Invalid stored policy judgment')
            cache = reviews/'api-cache'/(key+'.json')
            if json.loads(cache.read_text()) != result:
                raise ValueError('Embedded review differs from content-addressed cache')
            review_cache_sources[key] = digest(cache)
            if key not in receipts:
                matching = []
                for rawpath in (reviews/'api-cache').glob(key+'-raw-*.json'):
                    receipt = json.loads(rawpath.read_text())
                    raw = receipt['response']
                    if raw.get('id') != result['response_id']:
                        continue
                    choice = raw['choices'][0]
                    if (receipt['request'] != payload or raw.get('model') != model or
                            raw.get('provider') != result['provider'] or choice.get('finish_reason') != 'stop' or
                            parse_json_reply(choice['message']['content']) != judgment or raw.get('usage') != result['usage']):
                        raise ValueError('Raw provider receipt differs from accepted review')
                    matching.append({'path': str(rawpath.resolve()), 'sha256': digest(rawpath)})
                if not matching:
                    raise ValueError('Stored review lacks a matching raw provider receipt')
                receipts[key] = matching
            judgments.append(judgment)
        agreement = (len(judgments) == 2 and len({j['label'] for j in judgments}) == 1 and
                     all(j['confidence'] == 'high' for j in judgments) and not ep['truncated'])
        label = judgments[0]['label'] if agreement else 'uncertain'
        if row['agreement'] != agreement or row['label'] != label:
            raise ValueError('Consensus policy label differs from original rule')
    return {'episodes_verified': len(rows), 'review_slots': len(rows)*len(models),
            'accepted_review_slots': len(rows)*len(models)-absent, 'absent_review_slots': absent,
            'unique_accepted_requests': len(receipts), 'episode_file_sha256': episode_sources,
            'review_cache_sha256': review_cache_sources, 'raw_receipts': receipts,
            'audits_sha256': digest(audits_path), 'bank_sha256': digest(bank_path),
            'reviews_sha256': digest(reviews/'policy-reviews.json'),
            'completion_sha256': digest(reviews/'complete.json'), 'code_sha256': digest(__file__),
            'scope': 'Offline integrity only. Exact simulator replay, blinded reviewer payload, cache/raw response, typed action and consensus rule verified. Missing reviews stay missing. No inference, changed labels, detector performance or test-outcome summaries.'}


def main():
    p = argparse.ArgumentParser()
    for name in ['episodes', 'bank', 'audits', 'reviews', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('Preserve prior integrity report')
    report = verify(a.episodes, a.bank, a.audits, a.reviews)
    write_json(a.out, report)
    print(json.dumps({key: report[key] for key in ['episodes_verified', 'review_slots', 'accepted_review_slots', 'absent_review_slots', 'unique_accepted_requests']}))


if __name__ == '__main__':
    main()
