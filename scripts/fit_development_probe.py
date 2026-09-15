"""Fixed development probe with grouped out-of-fold predictions; not final evaluation."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    import numpy as np,sklearn
    from safetensors.numpy import load_file
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score,average_precision_score
    out=ROOT/'runs/development-probe';out.mkdir(parents=True,exist_ok=True)
    positions=ROOT/'runs/development-positions.json';labels=ROOT/'runs/confirmation/review-summary.json'
    rows=json.loads(positions.read_text())['rows'];lookup={x['episode_id']:x for x in json.loads(labels.read_text())['rows']}
    # Wait for both disjoint replay jobs, even when individual early rows exist.
    for i in range(2):
        folder=ROOT/f'runs/replay-{i}';complete=json.loads((folder/'complete.json').read_text())
        for name,sha in complete['files_sha256'].items():assert digest(folder/name)==sha
    provenance={'scope':'DEVELOPMENT ONLY; fixed L21 C=1 pipeline pilot, no final threshold or test evaluation','layer':21,'C':1.0,'positions_sha256':digest(positions),'labels_sha256':digest(labels),'script_sha256':digest(Path(__file__)),'sklearn':sklearn.__version__,'replay_complete_sha256':[digest(ROOT/f'runs/replay-{i}/complete.json') for i in range(2)]}
    if (out/'complete.json').exists():
        assert json.loads((out/'manifest.json').read_text())==provenance;return
    x=[];y=[];groups=[];ids=[];excluded=[];sources=[]
    for row in rows:
        eid=row['episode_id'];label=lookup[eid]['label']
        if label not in ('misaligned','benign') or 'unavailable' in row:
            excluded.append({'episode_id':eid,'reason':'uncertain label or unavailable position'});continue
        matches=list(ROOT.glob(f'runs/replay-*/{eid}.json'));matches=[p for p in matches if p.parent.name in ('replay-0','replay-1')];assert len(matches)==1
        replay=json.loads(matches[0].read_text());checks=[c for c in replay['checks'] if c['offset']=='0']
        assert len(checks)==4
        if not all(c['passed'] for c in checks):excluded.append({'episode_id':eid,'reason':'primary replay parity failed'});continue
        epfile=ROOT/'runs/confirmation'/eid/'episode.json';ep=json.loads(epfile.read_text());statefile=epfile.with_name('activations.safetensors')
        assert digest(epfile)==row['episode_sha256'] and digest(statefile)==row['activation_sha256']
        x.append(load_file(str(statefile))['layer_21'][row['primary_sample_index']]);y.append(int(label=='misaligned'));ids.append(eid)
        # Group all CodeContests tasks together; simple families are explicit.
        groups.append(ep['family_id'] if isinstance(ep['family_id'],str) else 'codecontests')
        sources.append({'episode_id':eid,'activation_sha256':row['activation_sha256'],'replay_sha256':digest(matches[0])})
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y);groups=np.asarray(groups);assert np.isfinite(x).all() and len(set(y))==2
    def model():return make_pipeline(StandardScaler(),LogisticRegression(C=1.0,max_iter=3000,solver='lbfgs',random_state=20260915))
    pred=np.full(len(y),np.nan);folds=[]
    for group in sorted(set(groups)):
        test=groups==group;train=~test;assert len(set(y[train]))==2
        clf=model().fit(x[train],y[train]);pred[test]=clf.predict_proba(x[test])[:,1]
        folds.append({'held_out_development_family':group,'train_n':int(train.sum()),'validation_n':int(test.sum()),'auc':float(roc_auc_score(y[test],pred[test])) if len(set(y[test]))==2 else None})
    final=model().fit(x,y);scale=final[0];lr=final[1];direction=lr.coef_[0]/scale.scale_;intercept=float(lr.intercept_[0]-np.dot(direction,scale.mean_))
    native=x@direction+intercept;reference=final.decision_function(x);error=float(np.max(np.abs(native-reference)));assert error<1e-8
    # Constant columns remain finite through sklearn's unit scaling convention.
    np.savez(out/'weights.npz',mean=scale.mean_,scale=scale.scale_,coefficient=lr.coef_[0],intercept=lr.intercept_,native_direction=direction,native_intercept=intercept)
    (out/'manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (out/'inputs.json').write_text(json.dumps(sources,indent=2)+'\n')
    (out/'oof-predictions.json').write_text(json.dumps([{'episode_id':eid,'group':g,'label':int(label),'score':float(score)} for eid,g,label,score in zip(ids,groups,y,pred)],indent=2)+'\n')
    report={'n':len(y),'positive':int(y.sum()),'benign':int((1-y).sum()),'groups':folds,'development_oof_auc':float(roc_auc_score(y,pred)),'development_oof_auprc':float(average_precision_score(y,pred)),'native_score_max_error':error,'excluded':excluded,'weights_sha256':digest(out/'weights.npz'),'scope':provenance['scope'],'limitations':'four broad development groups, template/difficulty confounds; no final held-out claim; no calibration or 5% FPR threshold selected'}
    (out/'complete.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
