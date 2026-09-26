"""Evaluate the preregistered local-reader bridge; never query an API."""
import argparse
import json
from pathlib import Path
from contracts import fingerprint
from smoke import digest, write_json


def evaluate(references, results, manifest_sha256):
    rows = []
    for reference in references:
        result = results.get(reference['request_id'], {})
        if result and result.get('manifest_sha256') != manifest_sha256:
            raise ValueError('Mixed or stale reader manifests')
        score = result.get('judgment', {}).get('score')
        valid = (result.get('status') == 'ok' and type(score) is int and score in (0, 1, 2)
                 and result.get('judgment', {}).get('confidence') in ('high', 'medium', 'low'))
        rows.append({'request_id': reference['request_id'], 'reference_score': reference['reference_score'],
                     'local_score': score if valid else None, 'valid': valid,
                     'exact_agreement': valid and score == reference['reference_score']})
    n = len(rows)
    if not n:
        raise ValueError('Empty reference set')
    return {'n': n, 'valid_fraction': sum(r['valid'] for r in rows)/n,
            'exact_agreement_fraction': sum(r['exact_agreement'] for r in rows)/n, 'rows': rows}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bridge', type=Path, required=True)
    p.add_argument('--reader', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    protocol = json.loads((a.bridge/'protocol.json').read_text())
    for name in ('jobs', 'references'):
        if digest(a.bridge/(name+'.json')) != protocol[name+'_sha256']:
            raise ValueError('Bridge inputs changed')
    manifest_sha = fingerprint(json.loads((a.reader/'manifest.json').read_text()))
    references = json.loads((a.bridge/'references.json').read_text())['references']
    results = {}
    for ref in references:
        path = a.reader/'results'/(ref['request_id']+'.json')
        if path.exists():
            result = json.loads(path.read_text())
            if result['request_id'] != ref['request_id']:
                raise ValueError('Result identity mismatch')
            results[ref['request_id']] = result
    report = evaluate(references, results, manifest_sha)
    report.update(protocol_sha256=digest(a.bridge/'protocol.json'), manifest_sha256=manifest_sha)
    report['passed'] = (report['valid_fraction'] >= protocol['valid_json_fraction_min'] and
                        report['exact_agreement_fraction'] >= protocol['exact_reference_agreement_fraction_min'])
    report['score_recall'] = {}
    for score, minimum in protocol.get('minimum_score_recall', {}).items():
        subset = [row for row in report['rows'] if row['reference_score'] == int(score)]
        if not subset:
            raise ValueError('Missing registered reference class')
        recall = sum(row['exact_agreement'] for row in subset)/len(subset)
        report['score_recall'][score] = {'n': len(subset), 'exact_recall': recall, 'required': minimum}
        report['passed'] = report['passed'] and recall >= minimum
    write_json(a.out, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
