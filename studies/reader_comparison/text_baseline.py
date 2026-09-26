"""Supervised causal-text baseline with the same family folds and label budget."""
import argparse,json
from pathlib import Path
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
import joblib
from contracts import fingerprint,conservative_threshold
from smoke import write_json,digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--captures',type=Path,required=True);p.add_argument('--audits',type=Path,required=True);p.add_argument('--endpoint',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();audits={r['episode_id']:r for r in json.loads(a.audits.read_text())};cm=json.loads((a.captures/'manifest.json').read_text());rows=[]
 for path in sorted(a.captures.glob('*/complete.json')):
  d=path.parent;done=json.loads(path.read_text())
  if done['manifest_sha256']!=fingerprint(cm) or done['cells_sha256']!=digest(d/'cells.json'):raise ValueError('Changed capture metadata')
  cells=[r for r in json.loads((d/'cells.json').read_text()) if r['endpoint']==a.endpoint]
  if not cells:continue
  r=cells[0];label=audits[r['episode_id']]
  if r['split'] not in ['train','validation'] or label['condition']!='prohibited' or label['label'] is None:continue
  rows.append({'episode_id':r['episode_id'],'family_id':r['family_id'],'split':r['split'],'text':r['prefix_text'],'label':label['label']})
 train=[r for r in rows if r['split']=='train'];val=[r for r in rows if r['split']=='validation'];texts=[r['text'] for r in train];y=np.array([r['label'] for r in train]);groups=np.array([r['family_id'] for r in train])
 def model(c):return make_pipeline(TfidfVectorizer(ngram_range=(1,2),max_features=20000),LogisticRegression(C=c,solver='liblinear',max_iter=10000,tol=1e-6,class_weight='balanced',random_state=20260926))
 grid=[]
 for c in [.01,.1,1.,10.]:
  values=[]
  for it,iv in GroupKFold(4).split(texts,y,groups):
   if len(set(y[it]))<2 or len(set(y[iv]))<2:raise ValueError('One-class grouped fold')
   m=model(c).fit([texts[i] for i in it],y[it])
   if np.any(m[-1].n_iter_>=10000):raise ValueError('Unconverged text fold')
   values.append(float(roc_auc_score(y[iv],m.decision_function([texts[i] for i in iv]))))
  grid.append({'C':c,'cv_auc':float(np.mean(values)),'fold_auc':values})
 best=max(grid,key=lambda r:(r['cv_auc'],-r['C']));m=model(best['C']).fit(texts,y)
 if np.any(m[-1].n_iter_>=10000):raise ValueError('Unconverged text fit')
 scores=m.decision_function([r['text'] for r in val]);negative=[float(s) for r,s in zip(val,scores) if r['label']==0];threshold=conservative_threshold(negative)
 a.out.mkdir(parents=True,exist_ok=True)
 if (a.out/'lock.json').exists():raise ValueError('Already fitted; do not overwrite text baseline')
 joblib.dump(m,a.out/'model.joblib');write_json(a.out/'lock.json',{'identity':cm['identity'],'endpoint':a.endpoint,'capture_manifest_sha256':fingerprint(cm),'audits_sha256':digest(a.audits),'training_validation_rows_sha256':fingerprint(rows),'selected':best,'grid':grid,'threshold':threshold,'validation_benign_n':len(negative),'validation_false_positives':sum(s>=threshold for s in negative),'model_sha256':digest(a.out/'model.joblib'),'code_sha256':digest(__file__),'scope':'No activations, reader descriptions, or future text; vocabulary and C selected from training only. Test cases are not scored.'})
 print(json.dumps({'selected':best,'threshold':threshold,'validation_benign_n':len(negative)}),flush=True)
if __name__=='__main__':main()
