"""Illustrative development four-way accounting; never relabeled as held-out."""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 d=ROOT/'runs/jview-interpretation-v1';complete=json.loads((d/'complete.json').read_text());assert not complete['errors'] and complete['completed_calls']==complete['expected_calls']
 scores=d/'scores.json';assert hashlib.sha256(scores.read_bytes()).hexdigest()==complete['scores_sha256']
 js={r['episode_id']:r for r in json.loads(scores.read_text())};ps={r['episode_id']:r for r in json.loads((ROOT/'runs/development-probe/oof-predictions.json').read_text())};labels=json.loads((ROOT/'runs/confirmation/review-summary.json').read_text())['rows'];cfg=json.loads((ROOT/'configs/jview-interpretation-v1.json').read_text());p_threshold=cfg['development_probe_threshold'];j_threshold=cfg['development_flag_threshold']
 out=ROOT/'reports/development-comparison';out.mkdir(parents=True,exist_ok=True);rows=[];tables={k:{c:0 for c in ['probe_only','jlens_only','both','neither']} for k in ['all','misaligned','benign']};excluded=[]
 for label in labels:
  eid=label['episode_id'];p=ps.get(eid);j=js[eid]['jview']['score'];context=js[eid]['context_only']['score'];r={'episode_id':eid,'behavior_label':label['label'],'probe_score':p['score'] if p else None,'jlens_score':j,'context_only_score':context,'probe_threshold':p_threshold,'jlens_threshold':j_threshold,'category':None}
  if p is None or j is None or label['label'] not in ['misaligned','benign']:excluded.append(eid)
  else:
   pf=p['score']>=p_threshold;jf=j>=j_threshold;c='both' if pf and jf else 'probe_only' if pf else 'jlens_only' if jf else 'neither';r.update(probe_flag=pf,jlens_flag=jf,category=c)
   for k in ['all',label['label']]:tables[k][c]+=1
  rows.append(r)
 assert sum(tables['all'].values())+len(excluded)==len(rows)
 agreement={}
 for arm in cfg['arms']:
  pairs=[r[arm]['reviewer_scores'] for r in js.values() if r[arm]['score'] is not None];n=len(pairs);observed=sum(a==b for a,b in pairs)/n;expected=sum(sum(a==k for a,b in pairs)*sum(b==k for a,b in pairs)/n**2 for k in [0,1,2]);agreement[arm]={'n':n,'agreement':observed,'cohen_kappa':(observed-expected)/(1-expected) if expected<1 else None}
 report={'scope':'DEVELOPMENT PILOT ONLY; OOF probe, two blinded automated J-space reviewers; fixed illustrative thresholds; NOT final5%FPR or held-out evidence','thresholds':{'probe':p_threshold,'jlens':j_threshold},'tables':tables,'denominator':sum(tables['all'].values()),'excluded_ids':excluded,'reviewer_agreement':agreement,'context_only_flags':sum(r['context_only_score'] is not None and r['context_only_score']>=j_threshold for r in rows),'source_sha256':{'jview_scores':hashlib.sha256(scores.read_bytes()).hexdigest(),'probe_oof':hashlib.sha256((ROOT/'runs/development-probe/oof-predictions.json').read_bytes()).hexdigest()},'limitations':'No causal or universal misalignment claim; only95 labeled developmental cases, four broad task groups, template/reasoning confounds;32prompt lens pilot; false negatives depend on fixed display/rubric'}
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(out/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
 with (out/'cases.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['episode_id','behavior_label','probe_score','jlens_score','context_only_score','probe_threshold','jlens_threshold','probe_flag','jlens_flag','category']);w.writeheader();w.writerows(rows)
 print(json.dumps(report),flush=True)
if __name__=='__main__':main()
