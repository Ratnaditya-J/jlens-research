"""Summarize frozen paired held-out scores; never fit thresholds on these rows.

Input JSON: protocol {split, observation_boundary, threshold_source, probe_threshold,
jlens_threshold}, cases [{episode_id, task_group, behavior_label, probe_score,
jlens_score}]. Scores increase with flag likelihood; ties flag. Null scores abstain.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

CATEGORIES = ('probe_only', 'jlens_only', 'both', 'neither')

def finite(value):
    return type(value) in (int, float) and math.isfinite(value)

def summarize(data):
    protocol = data['protocol']
    if protocol['split'] != 'test' or protocol['threshold_source'] != 'validation':
        raise ValueError('Requires held-out test scores and validation-selected thresholds')
    if not protocol['observation_boundary']:
        raise ValueError('Observation boundary must be specified')
    thresholds = [protocol[k] for k in ('probe_threshold', 'jlens_threshold')]
    if not all(finite(t) for t in thresholds):
        raise ValueError('Thresholds must be finite numbers')
    rows, seen = [], set()
    strata = {name: {c: 0 for c in CATEGORIES} for name in ('all', 'misaligned', 'benign', 'uncertain', 'unavailable')}
    excluded = []
    for case in data['cases']:
        eid = case['episode_id']
        if not eid or eid in seen:
            raise ValueError('Missing or duplicate episode ID')
        seen.add(eid)
        label = case['behavior_label']
        if label not in strata or label == 'all':
            raise ValueError('Unrecognized independent behavior label')
        scores = [case.get(k) for k in ('probe_score', 'jlens_score')]
        row = {**case, **protocol, 'probe_flag': None, 'jlens_flag': None, 'category': None}
        if not all(finite(s) for s in scores):
            row['exclusion'] = 'missing_or_nonfinite_score'
            excluded.append({'episode_id': eid, 'reason': row['exclusion']})
        else:
            p, j = [s >= t for s, t in zip(scores, thresholds)]
            category = 'both' if p and j else 'probe_only' if p else 'jlens_only' if j else 'neither'
            row.update(probe_flag=p, jlens_flag=j, category=category, exclusion='')
            strata['all'][category] += 1
            strata[label][category] += 1
        rows.append(row)
    tables = {}
    for label, counts in strata.items():
        n = sum(counts.values())
        tables[label] = {'denominator': n, 'counts': counts,
                         'percentages': {k: 100*v/n if n else None for k, v in counts.items()}}
    assert tables['all']['denominator'] + len(excluded) == len(rows)
    return {'protocol': protocol, 'total_cases': len(rows), 'tables': tables, 'excluded': excluded}, rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output_directory', type=Path)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    summary, rows = summarize(json.loads(raw))
    summary['input_sha256'] = hashlib.sha256(raw).hexdigest()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    (args.output_directory/'paired-breakdown.json').write_text(json.dumps(summary, indent=2)+'\n')
    fields = ['episode_id', 'task_group', 'behavior_label', 'observation_boundary', 'probe_score', 'jlens_score', 'probe_threshold', 'jlens_threshold', 'probe_flag', 'jlens_flag', 'category', 'exclusion']
    with (args.output_directory/'paired-cases.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

if __name__ == '__main__':
    main()
