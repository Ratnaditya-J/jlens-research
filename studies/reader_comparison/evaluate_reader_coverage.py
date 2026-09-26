"""Evaluate a completed validation coverage pilot without outcome labels."""
import argparse
import json
from collections import Counter
from pathlib import Path
from collect_local_readers import valid_score
from contracts import fingerprint
from smoke import digest, write_json


def summarize(results, strata):
    ids = {rid for group in strata.values() for rid in group}
    if set(results) != ids or not ids or any(not group for group in strata.values()):
        raise ValueError('Incomplete or extraneous pilot requests')
    usable = {rid:valid_score(result) is not None for rid,result in results.items()}
    cells = {name:{'n':len(group), 'usable':sum(usable[rid] for rid in group)}
             for name,group in strata.items()}
    empty = [name for name,cell in cells.items() if not cell['usable']]
    errors = Counter(result.get('error','Invalid judgment schema')
                     for rid,result in results.items() if not usable[rid])
    fraction = sum(usable.values())/len(ids)
    return {'unique_requests':len(ids), 'usable_requests':sum(usable.values()),
            'usable_fraction':fraction, 'strata':cells, 'all_unavailable_strata':empty,
            'unavailable_errors':dict(errors), 'passed':fraction>=.9 and not empty,
            'rule':'At least90% schema-valid unique responses and no all-unavailable stratum.',
            'scope':'Engineering coverage only, not detector accuracy or interpretation faithfulness. Repeated strata share requests; no independence claim.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pilot', type=Path, required=True)
    p.add_argument('--reader', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('Preserve existing coverage report')
    pm = json.loads((a.pilot/'manifest.json').read_text())
    if pm['phase']!='validation' or pm['stage']!='coverage-pilot':
        raise ValueError('Only the registered validation pilot is allowed')
    for path,sha in pm['source_hashes'].items():
        if digest(path)!=sha:
            raise ValueError('Pilot source changed')
    if digest(a.pilot/'jobs.json')!=pm['jobs_sha256']:
        raise ValueError('Pilot jobs changed')
    rm = json.loads((a.reader/'manifest.json').read_text())
    rf = fingerprint(rm)
    done = json.loads((a.reader/'reader-coverage-pilot-jobs-complete.json').read_text())
    if done['manifest_sha256']!=rf or done['jobs_sha256']!=pm['jobs_sha256']:
        raise ValueError('Completion belongs to another pilot or execution')
    results, hashes = {}, {}
    for job in json.loads((a.pilot/'jobs.json').read_text())['jobs']:
        rid = job['request_id']
        if fingerprint({'system':job['system'],'evidence':job['evidence']})!=rid:
            raise ValueError('Request identity differs')
        path = a.reader/'results'/(rid+'.json')
        result = json.loads(path.read_text())
        if result['request_id']!=rid or result['manifest_sha256']!=rf:
            raise ValueError('Result belongs to another execution')
        results[rid], hashes[rid] = result, digest(path)
    report = summarize(results, pm['strata'])
    report.update(reader_manifest_sha256=digest(a.reader/'manifest.json'),
                  pilot_manifest_sha256=digest(a.pilot/'manifest.json'),
                  result_sha256=hashes, code_sha256=digest(__file__),
                  score_schema_code_sha256=digest(Path(__file__).with_name('collect_local_readers.py')))
    write_json(a.out, report)
    print({k:report[k] for k in ['unique_requests','usable_requests','usable_fraction','all_unavailable_strata','passed']})


if __name__ == '__main__':
    main()
