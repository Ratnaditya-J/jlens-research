"""Lock a distinct local-judge GPT-OSS extension using validation data only."""
import argparse
import json
from pathlib import Path
import numpy as np
import joblib
from contracts import conservative_threshold, fingerprint
from legacy_local_jobs import ARMS
from smoke import digest, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--interpretations', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    im = json.loads((a.interpretations/'manifest.json').read_text())
    done = json.loads((a.interpretations/'complete.json').read_text())
    if im.get('study') != 'archived-gptoss-local-extension-v1' or im['phase'] != 'validation' or im['dataset'] != 'fresh' or im['offset'] != 0:
        raise ValueError('Expected the separate code-onset local validation protocol')
    if done['manifest_sha256'] != fingerprint(im) or done['scores_sha256'] != digest(a.interpretations/'scores.json'):
        raise ValueError('Changed local validation judgments')
    if fingerprint(im['reader_protocol']) != im['reader_protocol_sha256']:
        raise ValueError('Changed local reader protocol')
    hashes = dict(im['source_hashes'])
    for path, sha in hashes.items():
        if digest(path) != sha:
            raise ValueError('Changed local reader provenance')
    data = a.repo/'runs/fresh-assembled'
    oldcal = a.repo/'runs/fresh-calibration'
    original = json.loads((oldcal/'lock.json').read_text())
    records = json.loads((data/'validation-records.json').read_text())
    scores = {row['episode_id']: row for row in json.loads((a.interpretations/'scores.json').read_text())}
    model = joblib.load(oldcal/'probe.joblib')
    x = np.load(data/'validation-features.npz', allow_pickle=False)['layer_'+str(original['selected']['layer'])]
    ps = model.predict_proba(x.astype(np.float64))[:, 1]
    if not np.isfinite(ps).all():
        raise ValueError('Nonfinite original validation probe scores')
    thresholds, arms = {}, {}
    for arm in ARMS:
        usable = [row for row in records if row['label'] == 'benign' and scores.get(row['episode_id'], {}).get(arm, {}).get('score') is not None]
        values = [scores[row['episode_id']][arm]['score'] for row in usable]
        threshold = conservative_threshold(values, .05)
        fpr = sum(value >= threshold for value in values)/len(values)
        matched = [float(ps[row['feature_index']]) for row in usable if row['feature_index'] is not None]
        thresholds[arm] = threshold
        arms[arm] = {'validation_benign_n': len(values), 'validation_fpr': fpr,
                     'missing_validation_benign': sum(row['label'] == 'benign' for row in records)-len(values),
                     'matched_probe_threshold': conservative_threshold(matched, fpr),
                     'matched_probe_validation_n': len(matched)}
    sources = [data/'validation-records.json', data/'validation-features.npz', oldcal/'lock.json', oldcal/'probe.joblib',
               a.interpretations/'scores.json', a.interpretations/'manifest.json', a.interpretations/'complete.json',
               Path(__file__), Path(__file__).with_name('legacy_local_jobs.py'),
               Path(__file__).with_name('evaluate_legacy_local.py'), Path(__file__).with_name('metrics.py'),
               Path(__file__).with_name('contracts.py')]
    hashes.update({str(path.resolve()): digest(path) for path in sources})
    lock = {'study': im['study'], 'offset': 0, 'arms': arms, 'thresholds': thresholds,
            'original_probe_threshold': original['probe_threshold'], 'reader_protocol_sha256': im['reader_protocol_sha256'],
            'interpreter_code_sha256': im['interpreter_code_sha256'], 'source_hashes': hashes,
            'scope': 'Independent local-judge extension, fresh code-onset validation only. Archived probe and premium judgments are unchanged; same frozen thresholds apply to all local stress panels.'}
    if a.out.exists():
        raise ValueError('Preserve existing local validation lock')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(a.out, lock)
    print(json.dumps({'thresholds': thresholds, 'arms': arms}))


if __name__ == '__main__':
    main()
