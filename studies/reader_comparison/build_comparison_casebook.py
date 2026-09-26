"""Audit fixed held-out disagreement cases; never select by interesting prose."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from collect_local_readers import load_jobs, load_results, aggregate
from contracts import fingerprint
from local_reader_jobs import review_jobs, validate_rows
from smoke import digest, write_json


def read(path):
    return json.loads(Path(path).read_text())


def fixed_selection(rows, thresholds):
    arms = ['raw_probe', 'j_summary_context', 'oracle_context']
    groups = {}
    for row in rows:
        if row['condition'] != 'prohibited' or row['label'] not in (0, 1):
            continue
        if any(row['scores'].get(arm) is None for arm in arms):
            continue
        flags = tuple(arm for arm in arms if row['scores'][arm] >= thresholds[arm])
        groups.setdefault((row['label'], flags), []).append(row['episode_id'])
    return [{'label': label, 'flags': list(flags),
             'ids': sorted(ids, key=lambda s: hashlib.sha256(s.encode()).hexdigest())[:3]}
            for (label, flags), ids in sorted(groups.items())]


def canonical_selection(selection):
    return sorted(selection, key=lambda r: (r['label'], tuple(r['flags'])))


def fenced(value):
    """Preserve arbitrary readout text as data, including embedded Markdown fences."""
    text = json.dumps(value, indent=2, ensure_ascii=False)
    longest = max((len(m[0]) for m in re.finditer(r'`+', text)), default=0)
    fence = '`' * max(3, longest + 1)
    return fence + 'json\n' + text + '\n' + fence


def check_sources(manifest):
    for path, expected in manifest.get('source_hashes', {}).items():
        if digest(path) != expected:
            raise ValueError('Source artifact changed: ' + path)


def main():
    p = argparse.ArgumentParser()
    for name in ('report', 'lock', 'bundle', 'summaries', 'jobs', 'interpretations', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--readers', type=Path, nargs=2, required=True)
    a = p.parse_args()
    lock, report = read(a.lock), read(a.report/'summary.json')
    cases = read(a.report/'cases.json')
    check_sources(lock)
    if report['lock_sha256'] != digest(a.lock) or report['endpoint'] != lock['endpoint'] or report['identity'] != lock['identity']:
        raise ValueError('Report and calibration identity differ')
    selection = fixed_selection(cases, lock['thresholds'])
    if selection != canonical_selection(report['casebook_selection']):
        raise ValueError('Report case selection is not the fixed hash-based sample')
    prepared, jobs, aliases = load_jobs(a.jobs)
    bundle, summaries = read(a.bundle), read(a.summaries)
    if prepared['phase'] != 'test' or prepared['stage'] != 'reviews':
        raise ValueError('Casebooks require completed held-out review jobs')
    if prepared['bundle_sha256'] != digest(a.bundle) or prepared['summaries_sha256'] != digest(a.summaries):
        raise ValueError('Readout bundle or summaries changed')
    if bundle['subject_identity'] != lock['identity'] or bundle['endpoint'] != lock['endpoint']:
        raise ValueError('Readouts belong to another checkpoint or endpoint')
    if summaries['bundle_sha256'] != digest(a.bundle) or summaries['phase'] != 'test':
        raise ValueError('Summary provenance differs')
    check_sources(summaries)
    blinded = validate_rows(bundle, 'test')
    expected_jobs, expected_aliases, donors = review_jobs(blinded, summaries['summaries'])
    if sorted(expected_jobs, key=lambda r: r['request_id']) != jobs or expected_aliases != aliases or donors != prepared['donors']:
        raise ValueError('Judge evidence differs from the registered arm construction')
    im, done = read(a.interpretations/'manifest.json'), read(a.interpretations/'complete.json')
    check_sources(im)
    if any(im.get(key) != value for key, value in prepared.items()):
        raise ValueError('Interpretations do not use these exact prepared jobs')
    if done['manifest_sha256'] != fingerprint(im) or done['scores_sha256'] != digest(a.interpretations/'scores.json'):
        raise ValueError('Interpretation completion hashes differ')
    if fingerprint(im['reader_protocol']) != lock['reader_protocol_sha256']:
        raise ValueError('Interpretation protocol differs from calibration')
    pairs = [load_results(directory, jobs) for directory in a.readers]
    if [m for m, _ in pairs] != im['reader_protocol']['readers']:
        raise ValueError('Reader execution identity or order differs')
    reconstructed = aggregate(aliases, [r for _, r in pairs], prepared['arms'])
    if reconstructed != read(a.interpretations/'scores.json'):
        raise ValueError('Raw judge outputs do not reproduce collected scores')
    by_score = {r['episode_id']: r for r in reconstructed}
    for case in cases:
        for arm in prepared['arms']:
            if case['scores'].get(arm) != by_score.get(case['episode_id'], {}).get(arm, {}).get('score'):
                raise ValueError('Reported case scores differ from raw judgments')
    by_case = {r['episode_id']: r for r in cases}
    by_blind = {r['episode_id']: r for r in blinded}
    by_job = {r['request_id']: r for r in jobs}
    records = []
    for group in selection:
        for eid in group['ids']:
            case, view = by_case[eid], by_blind[eid]
            reviews = []
            for alias in aliases:
                if alias['episode_id'] != eid:
                    continue
                rid = alias['request_id']
                reviews.append({'arm': alias['arm'], 'alias': alias,
                                'exact_request': by_job.get(rid),
                                'reader_outputs': [result.get(rid) for _, result in pairs]})
            records.append({'episode_id': eid, 'selection_group': group,
                            'behavior_and_confirmation': case,
                            'operating_points': {arm: {'score': case['scores'].get(arm), 'threshold': threshold,
                                                      'flag': None if case['scores'].get(arm) is None else case['scores'][arm] >= threshold}
                                                 for arm, threshold in lock['thresholds'].items()},
                            'exact_readouts_and_prefix': view,
                            'summaries': summaries['summaries'].get(eid),
                            'shuffled_donor_episode_id': donors.get(view['prefix_sha256']),
                            'reviews': reviews,
                            'manual_fidelity_assessment': None})
    files = [a.lock, a.report/'summary.json', a.report/'cases.json', a.bundle, a.summaries,
             a.jobs/'manifest.json', a.jobs/'jobs.json', a.jobs/'aliases.json',
             a.interpretations/'manifest.json', a.interpretations/'scores.json', a.interpretations/'complete.json', Path(__file__)]
    files.extend(directory/'manifest.json' for directory in a.readers)
    files.extend(directory/'results'/(job['request_id']+'.json') for directory in a.readers for job in jobs
                 if (directory/'results'/(job['request_id']+'.json')).exists())
    artifact = {'endpoint': lock['endpoint'], 'identity': lock['identity'], 'selection': selection,
                'source_hashes': {str(path.resolve()): digest(path) for path in files}, 'cases': records,
                'scope': 'Fixed sample of complete three-way judgments. Missing readouts are reported by the quantitative coverage analysis, not represented as negatives here. Generated descriptions and judge rationales are untrusted hypotheses. A raw-probe hit with a J-display miss does not establish information loss in the full J transform. Manual semantic fidelity assessment remains outstanding.'}
    a.out.mkdir(parents=True, exist_ok=True)
    if any(a.out.iterdir()):
        raise ValueError('Preserve existing casebook output')
    write_json(a.out/'casebook.json', artifact)
    sections = ['# Held-out disagreement casebook', artifact['scope'],
                'For each case, examine whether descriptions merely restate the prefix, add supported activation-specific content, or introduce unsupported details. Judge failure, threshold choice, display compression, and full-transform coverage are separate questions. Missing rationale fields remain missing; this generator supplies no semantic verdict.']
    for record in records:
        sections += ['## ' + record['episode_id'], fenced(record)]
    (a.out/'casebook.md').write_text('\n\n'.join(sections) + '\n')
    write_json(a.out/'complete.json', {'cases': len(records), 'casebook_sha256': digest(a.out/'casebook.json'),
                                     'markdown_sha256': digest(a.out/'casebook.md')})
    print(json.dumps({'selected_cases': len(records), 'endpoint': lock['endpoint']}))


if __name__ == '__main__':
    main()
