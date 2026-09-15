"""Matched family folds and information boundaries for development text controls."""
import json,hashlib
from pathlib import Path
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'runs/development-permitted-text.json';texts={r['episode_id']:r for r in json.loads(p.read_text())['rows']}
oof=ROOT/'runs/development-probe/oof-predictions.json';rows=json.loads(oof.read_text());y=np.array([r['label'] for r in rows]);g=np.array([r['group'] for r in rows]);output={}
for arm in ['prompt_only','permitted_prefix']:
 x=np.array([texts[r['episode_id']]['prompt']+ ('\n'+texts[r['episode_id']]['generated_prefix'] if arm=='permitted_prefix' else '') for r in rows]);pred=np.zeros(len(rows));folds=[]
 for group in sorted(set(g)):
  test=g==group;train=~test
  clf=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=1,max_features=20000),LogisticRegression(C=1,max_iter=3000,random_state=20260915)).fit(x[train],y[train]);pred[test]=clf.predict_proba(x[test])[:,1]
  folds.append({'group':group,'auc':float(roc_auc_score(y[test],pred[test])) if len(set(y[test]))==2 else None})
 output[arm]={'development_oof_auc':float(roc_auc_score(y,pred)),'folds':folds,'scores':[{'episode_id':r['episode_id'],'score':float(s)} for r,s in zip(rows,pred)]}
report={'scope':'development text controls, same95cases and whole-family folds as activation pilot; no held-out claim','text_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'fold_sha256':hashlib.sha256(oof.read_bytes()).hexdigest(),'arms':output}
(ROOT/'runs/development-text-baselines.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({a:r['development_oof_auc'] for a,r in output.items()}))
