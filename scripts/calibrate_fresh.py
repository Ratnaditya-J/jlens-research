"""Train-only model selection and validation-only thresholds; test files never read."""
import argparse,hashlib,json,sys,warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.thresholds import fpr_threshold

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import numpy as np,joblib,sklearn
 from sklearn.pipeline import make_pipeline
 from sklearn.preprocessing import StandardScaler
 from sklearn.linear_model import LogisticRegression
 from sklearn.model_selection import GroupKFold
 from sklearn.metrics import roc_auc_score
 from sklearn.feature_extraction.text import TfidfVectorizer
 from sklearn.exceptions import ConvergenceWarning
 warnings.filterwarnings('error',category=ConvergenceWarning)
 parser=argparse.ArgumentParser();parser.add_argument('--offset',type=int,choices=[0,32,64],default=0);args=parser.parse_args();suffix=f'-offset{args.offset}' if args.offset else '';data=ROOT/f'runs/fresh{suffix}-assembled';out=ROOT/f'runs/fresh{suffix}-calibration';out.mkdir(parents=True,exist_ok=True)
 if (out/'lock.json').exists():raise RuntimeError('Calibration already locked; do not refit')
 records={s:json.loads((data/(s+'-records.json')).read_text()) for s in ['train','validation']};arrays={s:np.load(data/(s+'-features.npz')) for s in records}
 eligible={s:[r for r in records[s] if r['feature_index'] is not None and r['label'] in ['misaligned','benign']] for s in records}
 ys={s:np.array([r['label']=='misaligned' for r in eligible[s]],dtype=int) for s in records};groups=np.array([r['family_id'] for r in eligible['train']]);assert len(set(groups))>=4
 assert all(len(set(ys[s]))==2 for s in ys)
 def x(s,l):return arrays[s][f'layer_{l}'][[r['feature_index'] for r in eligible[s]]].astype(np.float64)
 def model(c):return make_pipeline(StandardScaler(),LogisticRegression(C=c,max_iter=5000,random_state=20260916))
 grid=[]
 for l in [7,15,21,22]:
  for c in [.01,.1,1,10]:
   values=[]
   for train,valid in GroupKFold(n_splits=4).split(x('train',l),ys['train'],groups):
    assert len(set(ys['train'][train]))==len(set(ys['train'][valid]))==2
    fitted=model(c).fit(x('train',l)[train],ys['train'][train]);values.append(float(roc_auc_score(ys['train'][valid],fitted.predict_proba(x('train',l)[valid])[:,1])))
   grid.append({'layer':l,'C':c,'mean_train_group_cv_auc':sum(values)/len(values),'fold_auc':values})
 best=sorted(grid,key=lambda r:(-r['mean_train_group_cv_auc'],r['C'],r['layer']))[0];l=best['layer'];fitted=model(best['C']).fit(x('train',l),ys['train']);p=fitted.predict_proba(x('validation',l))[:,1];threshold=fpr_threshold(p[ys['validation']==0]);joblib.dump(fitted,out/'probe.joblib')
 sc,lr=fitted[0],fitted[1];direction=lr.coef_[0]/sc.scale_;intercept=float(lr.intercept_[0]-direction@sc.mean_);error=float(np.max(np.abs(x('validation',l)@direction+intercept-fitted.decision_function(x('validation',l)))));assert error<1e-8
 np.savez(out/'probe-native.npz',native_direction=direction,native_intercept=intercept,mean=sc.mean_,scale=sc.scale_,coefficient=lr.coef_[0],intercept=lr.intercept_)
 jdir=ROOT/f'runs/fresh{suffix}-jview-validation';jc=json.loads((jdir/'complete.json').read_text());assert not jc['errors'];assert sha(jdir/'scores.json')==jc['scores_sha256'];jlookup={r['episode_id']:r for r in json.loads((jdir/'scores.json').read_text())}
 jthresholds={}
 for arm in ['jview','context_only']:
  negatives=[jlookup[r['episode_id']][arm]['score'] for r in eligible['validation'] if r['label']=='benign' and jlookup[r['episode_id']][arm]['score'] is not None];jthresholds[arm]=fpr_threshold(negatives)
 jneg=[jlookup[r['episode_id']]['jview']['score'] for r in eligible['validation'] if r['label']=='benign' and jlookup[r['episode_id']]['jview']['score'] is not None]
 j_achieved_fpr=sum(v>=jthresholds['jview'] for v in jneg)/len(jneg)
 matched_probe_threshold=fpr_threshold(p[ys['validation']==0],j_achieved_fpr)
 baselines={};contexts={s:{r['episode_id']:r for r in json.loads((data/(s+'-contexts.json')).read_text())['rows']} for s in records}
 for arm in ['prompt_only','permitted_prefix']:
  def texts(s):return [contexts[s][r['episode_id']]['prompt']+('\n'+contexts[s][r['episode_id']]['generated_prefix'] if arm=='permitted_prefix' else '') for r in eligible[s]]
  clf=make_pipeline(TfidfVectorizer(ngram_range=(1,2),max_features=20000),LogisticRegression(C=1,max_iter=5000,random_state=20260916)).fit(texts('train'),ys['train']);scores=clf.predict_proba(texts('validation'))[:,1];baselines[arm]={'threshold':fpr_threshold(scores[ys['validation']==0]),'validation_auc':float(roc_auc_score(ys['validation'],scores))};joblib.dump(clf,out/(arm+'.joblib'))
 z=sc.transform(x('train',l));delta=z[ys['train']==1].mean(axis=0)-z[ys['train']==0].mean(axis=0);mean_scores=sc.transform(x('validation',l))@delta;baselines['mean_difference']={'threshold':fpr_threshold(mean_scores[ys['validation']==0])};np.savez(out/'mean-difference.npz',direction=delta,mean=sc.mean_,scale=sc.scale_)
 shuffled=np.random.default_rng(20260916).permutation(ys['train']);null=model(best['C']).fit(x('train',l),shuffled);null_scores=null.predict_proba(x('validation',l))[:,1];baselines['shuffled_label_probe']={'threshold':fpr_threshold(null_scores[ys['validation']==0]),'validation_auc':float(roc_auc_score(ys['validation'],null_scores))};joblib.dump(null,out/'shuffled-label.joblib')
 random_config=json.loads((ROOT/'configs/random-direction-control.json').read_text());assert random_config['count']==20 and random_config['seed']==20260919
 random_directions=np.random.default_rng(random_config['seed']).normal(size=(random_config['count'],x('train',l).shape[1]));random_directions/=np.linalg.norm(random_directions,axis=1,keepdims=True)
 random_scores=sc.transform(x('validation',l))@random_directions.T
 random_thresholds=[fpr_threshold(random_scores[ys['validation']==0,i]) for i in range(20)]
 np.savez(out/'random-directions.npz',directions=random_directions,mean=sc.mean_,scale=sc.scale_)
 baselines['random_directions']={'seed':20260919,'count':20,'thresholds':random_thresholds,'scope':'Fixed random unit directions in training-standardized space at primary selected layer; descriptive distribution, no best-direction selection'}
 report={'offset_before_code_onset':args.offset,'scope':'Calibration lock: train-only grouped tuning, validation-only operating points; no test records, features or scores read','selected':best,'training_grid':grid,'probe_threshold':threshold,'matched_probe_threshold':matched_probe_threshold,'jview_validation_fpr':j_achieved_fpr,'jview_threshold':jthresholds['jview'],'context_only_threshold':jthresholds['context_only'],'target_fpr':.05,'native_score_max_error':error,'validation_probe_auc':float(roc_auc_score(ys['validation'],p)),'validation_probe_fpr':float(np.mean(p[ys['validation']==0]>=threshold)),'counts':{s:{'eligible':len(eligible[s]),'positive':int(ys[s].sum()),'benign':int((1-ys[s]).sum())} for s in records},'baselines':baselines,'sklearn':sklearn.__version__,'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'configs/final-protocol.json',ROOT/'configs/random-direction-control.json',ROOT/'manifests/fresh-splits.json',data/'manifest.json',data/'train-records.json',data/'validation-records.json',data/'train-features.npz',data/'validation-features.npz',jdir/'scores.json',Path(__file__)]},'artifacts':{p.name:sha(p) for p in out.iterdir() if p.suffix in ['.npz','.joblib']}}
 (out/'lock.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['training_grid','source_hashes','artifacts']}),flush=True)
if __name__=='__main__':main()
