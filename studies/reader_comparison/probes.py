"""Matched raw/J-space probes, family-held-out selection and validation thresholds.

Input JSON: identity, feature_sha256, and rows (episode_id, family_id, split,
layer, endpoint, label); NPZ: X_raw and X_jspace with exactly one vector per row.
This script fits from train/validation only and deliberately never scores test.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from contracts import conservative_threshold, fingerprint
from smoke import write_json, digest


def validate_rows(rows):
    family_split={}; seen=set()
    for row in rows:
        group=row['family_id'];split=row['split']
        if group in family_split and family_split[group]!=split:raise ValueError('Family split leakage')
        family_split[group]=split
        key=(row['episode_id'],row['endpoint'],row['layer'])
        if key in seen:raise ValueError('Duplicate feature cell')
        seen.add(key)
        if row['label'] not in [0,1,None]:raise ValueError('Invalid independent label')


def fit_probe(X, rows, endpoint, seed=20260926):
    validate_rows(rows)
    selected=[i for i,r in enumerate(rows) if r['endpoint']==endpoint and r['split']=='train' and r['label'] is not None and r.get('condition','prohibited')=='prohibited']
    layers=sorted({rows[i]['layer'] for i in selected})
    candidates=[]
    for layer in layers:
        indices=[i for i in selected if rows[i]['layer']==layer]
        y=np.array([rows[i]['label'] for i in indices]);groups=np.array([rows[i]['family_id'] for i in indices])
        if len(set(groups))<4:raise ValueError('At least four training families required for selection')
        if len(set(y))!=2:raise ValueError('Both outcome classes required')
        for c in [.01,.1,1.,10.]:
            scores=[]
            for train,test in GroupKFold(n_splits=4).split(X[indices],y,groups):
                if len(set(y[train]))<2 or len(set(y[test]))<2:raise ValueError('One-class family fold; redesign split before evaluation')
                model=make_pipeline(StandardScaler(),LogisticRegression(C=c,solver='liblinear',dual=True,max_iter=5000,class_weight='balanced',random_state=seed))
                model.fit(X[np.array(indices)[train]],y[train])
                scores.append(roc_auc_score(y[test],model.decision_function(X[np.array(indices)[test]])))
            candidates.append({'layer':layer,'C':c,'cv_auc':float(np.mean(scores)),'fold_auc':scores})
    if not candidates:raise ValueError('No training features for endpoint')
    best=max(candidates,key=lambda c:(c['cv_auc'],-c['C'],-c['layer']))
    train=[i for i in selected if rows[i]['layer']==best['layer']]
    validation=[i for i,r in enumerate(rows) if r['endpoint']==endpoint and r['layer']==best['layer'] and r['split']=='validation' and r['label'] is not None and r.get('condition','prohibited')=='prohibited']
    if not validation:raise ValueError('Independent validation set required')
    model=make_pipeline(StandardScaler(),LogisticRegression(C=best['C'],solver='liblinear',dual=True,max_iter=5000,class_weight='balanced',random_state=seed))
    model.fit(X[train],[rows[i]['label'] for i in train])
    scaler,linear=model.steps[0][1],model.steps[1][1]
    if np.any(linear.n_iter_>=5000):raise RuntimeError('Unconverged probe')
    weights=linear.coef_[0]/scaler.scale_
    intercept=float(linear.intercept_[0]-np.dot(weights,scaler.mean_))
    native=X[validation]@weights+intercept
    if not np.allclose(native,model.decision_function(X[validation]),rtol=1e-6,atol=1e-6):raise RuntimeError('Exported detector differs from fitted pipeline')
    benign=[float(score) for i,score in zip(validation,native) if rows[i]['label']==0]
    threshold=conservative_threshold(benign,.05)
    return {'endpoint':endpoint,'selected':best,'selection_candidates':candidates,'weights':weights.tolist(),'intercept':intercept,'threshold':threshold,'decision_rule':'score >= threshold','validation_benign_n':len(benign),'validation_false_positives':sum(s>=threshold for s in benign),'seed':seed,'scope':'Scores are logits of a class-balanced classifier, not calibrated probabilities. Test outcomes are not used for selection, fitting or thresholds.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--features',type=Path,required=True);p.add_argument('--endpoint',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text())
    if digest(a.features)!=manifest['feature_sha256']:raise ValueError('Feature provenance mismatch')
    arrays=np.load(a.features,allow_pickle=False);rows=manifest['rows'];a.out.mkdir(parents=True,exist_ok=True)
    for arm in ['raw','jspace']:
        x=arrays['X_'+arm]
        if x.ndim!=2 or x.shape[0]!=len(rows) or not np.isfinite(x).all():raise ValueError('Malformed feature matrix')
        result=fit_probe(x,rows,a.endpoint)
        result.update(arm=arm,identity=manifest['identity'],feature_manifest_sha256=fingerprint(manifest))
        write_json(a.out/(arm+'-probe.json'),result)


if __name__=='__main__':main()
