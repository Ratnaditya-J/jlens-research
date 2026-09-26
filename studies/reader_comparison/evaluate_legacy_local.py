"""Evaluate separately locked local GPT-OSS panels without altering archived results."""
import argparse
import hashlib
import json
from pathlib import Path
from contracts import fingerprint
from metrics import operating_point, paired_cluster_difference, disagreement_table
from smoke import digest, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--interpretations', type=Path, required=True)
    p.add_argument('--lock', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    lock = json.loads(a.lock.read_text())
    for path, sha in lock['source_hashes'].items():
        if digest(path) != sha:
            raise ValueError('Frozen local calibration artifact changed')
    im = json.loads((a.interpretations/'manifest.json').read_text())
    done = json.loads((a.interpretations/'complete.json').read_text())
    if im.get('study') != lock['study'] or im['offset'] != 0 or im['phase'] != 'test':
        raise ValueError('Wrong local test study')
    if done['manifest_sha256'] != fingerprint(im) or done['scores_sha256'] != digest(a.interpretations/'scores.json'):
        raise ValueError('Changed local test judgments')
    if im['interpreter_code_sha256'] != lock['interpreter_code_sha256'] or im['reader_protocol_sha256'] != lock['reader_protocol_sha256'] or fingerprint(im['reader_protocol']) != lock['reader_protocol_sha256']:
        raise ValueError('Local test execution differs from validation')
    for path, sha in im['source_hashes'].items():
        if digest(path) != sha:
            raise ValueError('Changed local test input')
    dataset = im['dataset']
    if dataset not in ['fresh', 'template-challenge', 'specificity-controls', 'monitor-controls']:
        raise ValueError('Unregistered local panel')
    records_path = a.repo/'runs'/(dataset+'-assembled')/'test-records.json'
    records = json.loads(records_path.read_text())
    original_directory = a.repo/'reports'/('final-comparison' if dataset == 'fresh' else dataset+'-comparison')
    original_path = original_directory/'cases.json'
    original = {row['episode_id']: row for row in json.loads(original_path.read_text())}
    scored = {row['episode_id']: row for row in json.loads((a.interpretations/'scores.json').read_text())}
    thresholds = dict(lock['thresholds'], probe=lock['original_probe_threshold'])
    rows = []
    for record in records:
        eid = record['episode_id']
        values = {arm: scored.get(eid, {}).get(arm, {}).get('score') for arm in lock['thresholds']}
        values['probe'] = original.get(eid, {}).get('probe_score')
        rows.append({'episode_id': eid, 'family_id': record['family_id'], 'original_label': record['label'],
                     'label': 1 if record['label'] == 'misaligned' else 0 if record['label'] == 'benign' else None,
                     'scores': values})
    known = [r for r in rows if r['label'] is not None]
    report = {'study': lock['study'], 'dataset': dataset, 'lock_sha256': digest(a.lock),
              'requested': len(rows), 'known_labels': len(known), 'thresholds': thresholds,
              'metrics': {}, 'paired_comparisons': {}, 'uncertain_as_benign': {},
              'source_hashes': {str(path.resolve()): digest(path) for path in [records_path, original_path, a.interpretations/'manifest.json', a.interpretations/'scores.json']},
              'scope': 'Separate local-reader supplement with validation-only thresholds. Original probe scores reused; local J-view/context baselines are separately judged. Stress and auxiliary contrasts are descriptive and exploratory; no causal or deployment claim.'}
    for arm, threshold in thresholds.items():
        usable = [r for r in known if r['scores'][arm] is not None]
        m = operating_point([r['label'] for r in usable], [r['scores'][arm] for r in usable], threshold)
        m['missing_known'] = len(known)-len(usable)
        for label, field in [(1, 'tpr'), (0, 'fpr')]:
            total = sum(r['label'] == label for r in known)
            missing = sum(r['label'] == label and r['scores'][arm] is None for r in known)
            found = m['tp' if label else 'fp']
            m['missingness_'+field+'_bounds'] = [found/total, (found+missing)/total] if total else None
        report['metrics'][arm] = m
        sensitivity = [r for r in rows if r['original_label'] in ['misaligned', 'benign', 'uncertain'] and r['scores'][arm] is not None]
        report['uncertain_as_benign'][arm] = operating_point([int(r['label'] == 1) for r in sensitivity], [r['scores'][arm] for r in sensitivity], threshold)
    pairs = [('jsummary', 'jview'), ('jsummary', 'probe'), ('jsummary', 'context_only'),
             ('jsummary', 'jsummary_shuffled'), ('jsummary_plus_tokens', 'jview'),
             ('jsummary_blind', 'jview_blind')]
    for aa, bb in pairs:
        paired = [r for r in known if r['scores'][aa] is not None and r['scores'][bb] is not None]
        y = [r['label'] for r in paired]
        sa, sb = [r['scores'][aa] for r in paired], [r['scores'][bb] for r in paired]
        groups = [r['family_id'] for r in paired]
        result = {'paired_n': len(paired), 'table': disagreement_table(y, {aa: [s >= thresholds[aa] for s in sa], bb: [s >= thresholds[bb] for s in sb]})}
        if len(set(groups)) >= 2:
            result['bootstrap'] = paired_cluster_difference(y, sa, sb, groups, thresholds[aa], thresholds[bb], seed=20260916)
        if bb == 'probe':
            result['matched_validation_specificity_probe'] = operating_point(y, sb, lock['arms'][aa]['matched_probe_threshold'])
        report['paired_comparisons'][aa+' minus '+bb] = result
    selection = {}
    primary = ['jsummary', 'probe', 'jview', 'context_only']
    for row in known:
        if any(row['scores'][arm] is None for arm in primary):
            continue
        flags = tuple(arm for arm in primary if row['scores'][arm] >= thresholds[arm])
        selection.setdefault((row['label'], flags), []).append(row['episode_id'])
    report['casebook_selection'] = [{'label': label, 'flags': flags,
                                    'ids': sorted(ids, key=lambda eid: hashlib.sha256(eid.encode()).hexdigest())[:3]}
                                   for (label, flags), ids in selection.items()]
    if a.out.exists():
        raise ValueError('Preserve completed local report')
    a.out.mkdir(parents=True)
    write_json(a.out/'summary.json', report)
    write_json(a.out/'cases.json', rows)
    print(json.dumps({'dataset': dataset, 'requested': len(rows), 'metrics': report['metrics']}))


if __name__ == '__main__':
    main()
