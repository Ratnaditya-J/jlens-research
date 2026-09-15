"""Secondary equal-budget linear classifier on full reference-transported states.

This is a supervised J-space probe, not the primary blinded J-view procedure.
Calibration reads train/validation only; evaluation requires its immutable lock.
"""
import argparse
import hashlib
import json
import sys
import warnings
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.thresholds import fpr_threshold

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    import joblib
    import numpy as np
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import roc_auc_score, average_precision_score
    from sklearn.exceptions import ConvergenceWarning
    warnings.filterwarnings('error', category=ConvergenceWarning)
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['calibrate', 'evaluate'])
    args = parser.parse_args()
    data = ROOT / 'runs/fresh-assembled'
    out = ROOT / 'runs/supervised-jspace'
    out.mkdir(parents=True, exist_ok=True)
    lockp = out / 'lock.json'
    def dataset(split):
        records = json.loads((data / (split + '-records.json')).read_text())
        records = [r for r in records if r['feature_index'] is not None and r['label'] in ['misaligned', 'benign']]
        features = np.load(data / (split + '-jspace-features.npz'))
        x = {l: features[f'layer_{l}'][[r['feature_index'] for r in records]].astype(np.float64) for l in [7,15,21,22]}
        y = np.array([r['label'] == 'misaligned' for r in records], dtype=int)
        return records, x, y
    def model(c):
        return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=5000, random_state=20260916))
    if args.stage == 'calibrate':
        assert not lockp.exists(), 'Secondary calibration already locked'
        records, x, y = dataset('train')
        _, vx, vy = dataset('validation')
        groups = [r['family_id'] for r in records]
        grid = []
        for l in [7,15,21,22]:
            for c in [.01,.1,1,10]:
                aucs = []
                for tr, va in GroupKFold(4).split(x[l], y, groups):
                    assert len(set(y[tr])) == len(set(y[va])) == 2
                    clf = model(c).fit(x[l][tr], y[tr])
                    aucs.append(float(roc_auc_score(y[va], clf.predict_proba(x[l][va])[:,1])))
                grid.append({'layer': l, 'C': c, 'mean_auc': sum(aucs)/len(aucs), 'fold_auc': aucs})
        best = sorted(grid, key=lambda r: (-r['mean_auc'], r['C'], r['layer']))[0]
        clf = model(best['C']).fit(x[best['layer']], y)
        scores = clf.predict_proba(vx[best['layer']])[:,1]
        threshold = fpr_threshold(scores[vy == 0])
        joblib.dump(clf, out / 'model.joblib')
        paths = [data / (s + suffix) for s in ['train','validation'] for suffix in ['-records.json','-jspace-features.npz']]
        paths += [Path(__file__), ROOT / 'configs/supervised-jspace.json']
        lock = {'selected': best, 'grid': grid, 'threshold': threshold,
                'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in paths},
                'model_sha256': sha(out / 'model.joblib'),
                'scope': 'Secondary supervised J-space probe; identical raw-probe layer/C budget, splits and training-only preprocessing; no test input read'}
        lockp.write_text(json.dumps(lock, indent=2) + '\n')
    else:
        lock = json.loads(lockp.read_text())
        for name, digest in lock['source_hashes'].items(): assert sha(ROOT / name) == digest
        assert sha(out / 'model.joblib') == lock['model_sha256']
        records, x, y = dataset('test')
        clf = joblib.load(out / 'model.joblib')
        scores = clf.predict_proba(x[lock['selected']['layer']])[:,1]
        flags = scores >= lock['threshold']
        report = {'scope': lock['scope'], 'n': len(y), 'threshold': lock['threshold'],
                  'selected': lock['selected'], 'auroc': float(roc_auc_score(y, scores)),
                  'auprc': float(average_precision_score(y, scores)),
                  'sensitivity': float(flags[y == 1].mean()), 'fpr': float(flags[y == 0].mean()),
                  'calibration_lock_sha256': sha(lockp),
                  'cases': [{'episode_id': r['episode_id'], 'family_id': r['family_id'], 'label': r['label'], 'score': float(s), 'flag': bool(f)} for r,s,f in zip(records,scores,flags)]}
        (out / 'test-report.json').write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__': main()
