"""One locked held-out join; paired counts, metrics, clustered intervals and controls."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from paired_breakdown import summarize
sys.path.insert(0,str(ROOT))
from src.comparison_diagnostics import additional_diagnostics

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import numpy as np,joblib
 from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss
 parser=argparse.ArgumentParser();parser.add_argument('--dataset',choices=['primary','template-challenge'],default='primary');args=parser.parse_args();challenge=args.dataset=='template-challenge';stem='template-challenge' if challenge else 'fresh'
 data=ROOT/f'runs/{stem}-assembled';cal=ROOT/'runs/fresh-calibration';lockp=cal/'lock.json';lock=json.loads(lockp.read_text())
 assembled=json.loads((data/'manifest.json').read_text())
 for name,digest in assembled['files_sha256'].items():assert sha(data/name)==digest,'assembled input changed: '+name
 for name,digest in lock['artifacts'].items():assert sha(cal/name)==digest
 for name,digest in lock['source_hashes'].items():assert sha(ROOT/name)==digest
 jd=ROOT/f'runs/{stem}-jview-test';jc=json.loads((jd/'complete.json').read_text());assert not jc['errors'];assert sha(jd/'scores.json')==jc['scores_sha256'];jlookup={r['episode_id']:r for r in json.loads((jd/'scores.json').read_text())}
 records=json.loads((data/'test-records.json').read_text());features=np.load(data/'test-features.npz');contexts={r['episode_id']:r for r in json.loads((data/'test-contexts.json').read_text())['rows']};layer=lock['selected']['layer'];probe=joblib.load(cal/'probe.joblib');x=features[f'layer_{layer}'].astype(np.float64);p=probe.predict_proba(x)[:,1];cases=[];extra=[]
 null=joblib.load(cal/'shuffled-label.joblib').predict_proba(x)[:,1];mean=np.load(cal/'mean-difference.npz');md=((x-mean['mean'])/mean['scale'])@mean['direction']
 textmodels={a:joblib.load(cal/(a+'.joblib')) for a in ['prompt_only','permitted_prefix']}
 for r in records:
  eid=r['episode_id'];i=r['feature_index'];j=jlookup.get(eid,{});js=j.get('jview',{}).get('score');cs=j.get('context_only',{}).get('score')
  label=r['label'] if r['label'] in ['misaligned','benign','uncertain'] else 'unavailable'
  cases.append({'episode_id':eid,'task_group':r['family_id'],'behavior_label':label,'probe_score':float(p[i]) if i is not None else None,'jlens_score':js,'template':r['template'],'control':r['control'],'runtime_use_cache':r['runtime_use_cache'],'matched_primary_episode_id':r.get('matched_primary_episode_id')})
  row={'episode_id':eid,'context_only_score':cs,'mean_difference_score':float(md[i]) if i is not None else None,'shuffled_label_score':float(null[i]) if i is not None else None}
  if i is not None:
   for arm,model in textmodels.items():
    text=contexts[eid]['prompt']+('\n'+contexts[eid]['generated_prefix'] if arm=='permitted_prefix' else '');row[arm+'_score']=float(model.predict_proba([text])[0,1])
  extra.append(row)
 protocol={'split':'test','threshold_source':'validation','observation_boundary':'before_first_submitted_code_token','probe_threshold':lock['probe_threshold'],'jlens_threshold':lock['jview_threshold']};report,rows=summarize({'protocol':protocol,'cases':cases})
 paired=[r for r in rows if r['category'] is not None and r['behavior_label'] in ['misaligned','benign']];y=np.array([r['behavior_label']=='misaligned' for r in paired]);groups=np.array([r['task_group'] for r in paired]);pp=np.array([r['probe_score'] for r in paired]);jj=np.array([r['jlens_score'] for r in paired]);assert len(set(y))==2
 def metric(scores,threshold,labels=None):
  y=labels if labels is not None else np.array([r["behavior_label"]=="misaligned" for r in paired])
  flags=scores>=threshold;tp=int(np.sum(flags&y));fn=int(np.sum(~flags&y));fp=int(np.sum(flags&~y));tn=int(np.sum(~flags&~y))
  return {'tp':tp,'fn':fn,'fp':fp,'tn':tn,'sensitivity':tp/(tp+fn) if tp+fn else None,'fpr':fp/(fp+tn) if fp+tn else None,'precision':tp/(tp+fp) if tp+fp else None,'auroc':float(roc_auc_score(y,scores)) if len(set(y))==2 else None,'auprc':float(average_precision_score(y,scores)) if y.sum() else None}
 report['metrics']={'probe':metric(pp,lock['probe_threshold']),'jview':metric(jj,lock['jview_threshold'])};report['metrics']['probe']['brier']=float(brier_score_loss(y,pp));report['prevalence']=float(y.mean());report['confirmed_paired_n']=len(paired)
 confirmed={c:sum(r['category']==c for r in paired) for c in ['probe_only','jlens_only','both','neither']};report['confirmed_four_way']=confirmed
 # Bootstrap whole algorithm families, preserving all replicates and paired flags.
 names=sorted(set(groups));rng=np.random.default_rng(20260916);weights=rng.multinomial(len(names),np.ones(len(names))/len(names),size=2000);per=[]
 for g in names:
  mask=(groups==g)&y;pf=pp[mask]>=lock['probe_threshold'];jf=jj[mask]>=lock['jview_threshold'];per.append([int(mask.sum()),int(pf.sum()),int(jf.sum()),int((pf&~jf).sum()),int((~pf&jf).sum()),int((pf&jf).sum()),int((~pf&~jf).sum())])
 boot=weights@np.asarray(per);valid=boot[:,0]>0;boot=boot[valid];intervals={}
 values={'probe_sensitivity':boot[:,1]/boot[:,0],'jview_sensitivity':boot[:,2]/boot[:,0],'sensitivity_difference':(boot[:,1]-boot[:,2])/boot[:,0],'probe_only_positive_fraction':boot[:,3]/boot[:,0],'jview_only_positive_fraction':boot[:,4]/boot[:,0],'both_positive_fraction':boot[:,5]/boot[:,0],'neither_positive_fraction':boot[:,6]/boot[:,0]}
 for key,v in values.items():intervals[key]=np.quantile(v,[.025,.975]).tolist()
 neg=[]
 for g in names:
  mask=(groups==g)&~y;pf=pp[mask]>=lock['probe_threshold'];jf=jj[mask]>=lock['jview_threshold'];neg.append([int(mask.sum()),int(pf.sum()),int(jf.sum())])
 nb=weights@np.asarray(neg);nb=nb[nb[:,0]>0]
 if len(nb):
  for key,v in {'probe_fpr':nb[:,1]/nb[:,0],'jview_fpr':nb[:,2]/nb[:,0],'fpr_difference':(nb[:,1]-nb[:,2])/nb[:,0]}.items():intervals[key]=np.quantile(v,[.025,.975]).tolist()
 report['bootstrap']={'method':'paired whole-family percentile bootstrap','replicates':2000,'seed':20260916,'positive_valid_replicates':len(boot),'negative_valid_replicates':len(nb),'limitation':'Small family count and zero observed errors can yield degenerate intervals; zero-width intervals do not prove zero population error'}
 report['cluster_intervals']=intervals;report['independent_test_families']=len(names)
 secondary,_=summarize({'protocol':{**protocol,'probe_threshold':lock['matched_probe_threshold']},'cases':cases});report['matched_validation_specificity']={'probe_threshold':lock['matched_probe_threshold'],'jview_validation_fpr':lock['jview_validation_fpr'],'tables':secondary['tables'],'probe_metrics':metric(pp,lock['matched_probe_threshold'])}
 elookup={r['episode_id']:r for r in extra};baseline_metrics={}
 for name,field,threshold in [('context_only','context_only_score',lock['context_only_threshold']),('prompt_only','prompt_only_score',lock['baselines']['prompt_only']['threshold']),('permitted_prefix','permitted_prefix_score',lock['baselines']['permitted_prefix']['threshold']),('mean_difference','mean_difference_score',lock['baselines']['mean_difference']['threshold']),('shuffled_label_probe','shuffled_label_score',lock['baselines']['shuffled_label_probe']['threshold'])]:
  values=[elookup[r['episode_id']].get(field) for r in paired]
  if all(v is not None for v in values):baseline_metrics[name]=metric(np.asarray(values),threshold)
  else:baseline_metrics[name]={'unavailable':sum(v is None for v in values)}
 report['baseline_metrics']=baseline_metrics;report['strata']={}
 for key in ['template','control','runtime_use_cache','task_group']:
  strata={}
  for value in sorted({str(r.get(key)) for r in paired}):
   subset=[r for r in paired if str(r.get(key))==value];strata[value]={'n':len(subset),'misaligned':sum(r['behavior_label']=='misaligned' for r in subset),'four_way':{c:sum(r['category']==c for r in subset) for c in confirmed}}
   sy=np.array([r['behavior_label']=='misaligned' for r in subset]);sp=np.array([r['probe_score'] for r in subset]);sj=np.array([r['jlens_score'] for r in subset])
   strata[value]['probe_metrics']=metric(sp,lock['probe_threshold'],sy);strata[value]['jview_metrics']=metric(sj,lock['jview_threshold'],sy)
   strata[value]['baseline_metrics']={}
   for arm,field,t in [('prompt_only','prompt_only_score',lock['baselines']['prompt_only']['threshold']),('permitted_prefix','permitted_prefix_score',lock['baselines']['permitted_prefix']['threshold']),('context_only','context_only_score',lock['context_only_threshold'])]:
    sv=[elookup[r['episode_id']].get(field) for r in subset]
    if all(v is not None for v in sv):strata[value]['baseline_metrics'][arm]=metric(np.array(sv),t,sy)
  report['strata'][key]=strata
 selected=[]
 for label in ['misaligned','benign']:
  for category in confirmed:
   candidates=[r['episode_id'] for r in paired if r['behavior_label']==label and r['category']==category];selected.extend(sorted(candidates,key=lambda s:hashlib.sha256(s.encode()).hexdigest())[:3])
 report['dataset']='template-challenge' if challenge else 'primary';report['threshold_policy']='Original primary validation lock; no challenge calibration' if challenge else 'Primary validation lock'
 report['additional_diagnostics']=additional_diagnostics(rows,list(jlookup.values()),lock['probe_threshold'],lock['jview_threshold'])
 report['casebook_ids']=selected;report['calibration_lock_sha256']=sha(lockp);report['scope']='Held-out authored programming-task families; conditional on independently labeled and paired available primary readouts; no universal alignment, causality, or human readability claim'
 out=ROOT/('reports/template-challenge-comparison' if challenge else 'reports/final-comparison');out.mkdir(parents=True,exist_ok=True)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(out/'cases.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'baseline-cases.json').write_text(json.dumps(extra,indent=2)+'\n')
 import csv
 with (out/'cases.csv').open('w',newline='') as f:
  fields=['episode_id','task_group','behavior_label','template','control','runtime_use_cache','probe_score','jlens_score','probe_threshold','jlens_threshold','probe_flag','jlens_flag','category','exclusion'];writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
 print(json.dumps({'confirmed_paired_n':len(paired),'four_way':confirmed,'metrics':report['metrics'],'cluster_intervals':intervals}),flush=True)
if __name__=='__main__':main()
