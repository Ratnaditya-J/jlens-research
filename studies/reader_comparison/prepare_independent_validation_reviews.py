"""Prepare validation-only review requests whose evidence needs no summaries."""
import argparse
import json
from pathlib import Path
from contracts import fingerprint
from local_reader_jobs import validate_rows, review_jobs
from smoke import digest, write_json


def independent_jobs(bundle):
    rows = validate_rows(bundle, 'validation')
    jobs, aliases, donors = review_jobs(rows, {})
    aliases = [a for a in aliases if not a['arm'].startswith('j_summary')]
    ids = {a['request_id'] for a in aliases if a['request_id'] is not None}
    return [j for j in jobs if j['request_id'] in ids], aliases, donors


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bundles', type=Path, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('Preserve existing prepared requests')
    jobs, records = {}, []
    for path in a.bundles:
        bundle = json.loads(path.read_text())
        prepared, aliases, donors = independent_jobs(bundle)
        for j in prepared:
            if fingerprint({'system': j['system'], 'evidence': j['evidence']}) != j['request_id']:
                raise ValueError('Request identity mismatch')
            jobs[j['request_id']] = j
        records.append({'bundle': str(path.resolve()), 'bundle_sha256': digest(path),
                        'endpoint': bundle['endpoint'], 'aliases': aliases, 'donors': donors})
    a.out.mkdir(parents=True)
    write_json(a.out/'jobs.json', {'jobs': sorted(jobs.values(), key=lambda x:x['request_id'])})
    write_json(a.out/'manifest.json', {'phase':'validation', 'stage':'summary-independent-reviews',
        'jobs_sha256':digest(a.out/'jobs.json'), 'inputs':records,
        'source_hashes':{str(p.resolve()):digest(p) for p in [Path(__file__), Path(__file__).with_name('local_reader_jobs.py'), Path(__file__).with_name('interpret_readers.py'), Path(__file__).with_name('contracts.py')]},
        'scope':'Partial inference cache only, never a complete comparison. Identical request builder and prefix-group donors to full reviews. No test requests or aggregate performance; summary arms remain pending.'})
    print(json.dumps({'unique_requests':len(jobs), 'endpoints':len(records)}))


if __name__ == '__main__':
    main()
