"""Paired locked summary comparison, explicit missingness and family uncertainty."""
import argparse,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'studies/reader_comparison'))
from smoke import write_json,digest
from metrics import operating_point,paired_cluster_difference,disagreement_table

def main():
 p=argparse.ArgumentParser();p.add_argument('--offset',type=int,default=0);p.add_argument('--dataset',default='fresh');a=p.parse_args();suffix=f'-offset{a.offset}' if a.offset else '';stem=a.dataset+suffix;lp=ROOT/f'runs/fresh{suffix}-jsummary-calibration/lock.json';lock=json.loads(lp.read_text())
 for path,sha in lock['source_hashes'].items():
  if digest(ROOT/path)!=sha:raise ValueError('Changed locked source')
 data=ROOT/f'runs/{stem}-assembled';sd=ROOT/f'runs/{stem}-jsummary-test';scorepath=sd/'scores.json';complete=json.loads((sd/'review-complete.json').read_text())
 if digest(scorepath)!=complete['scores_sha256']:raise ValueError('Score corruption')
 summary={r['episode_id']:r for r in json.loads(scorepath.read_text())};origdir=ROOT/('reports/final-comparison'+suffix if a.dataset=='fresh' else 'reports/'+a.dataset+'-comparison');orig={r['episode_id']:r for r in json.loads((origdir/'cases.json').read_text())};context={r['episode_id']:r for r in json.loads((origdir/'baseline-cases.json').read_text())};records=json.loads((data/'test-records.json').read_text());arms=list(lock['arms'])+['probe','jview','context_only'];thresholds={arm:lock['arms'][arm]['threshold'] for arm in lock['arms']};thresholds.update(probe=lock['original_probe_threshold'],jview=lock['original_jview_threshold'],context_only=lock['original_context_threshold']);rows=[]
 for r in records:
  eid=r['episode_id'];scores={arm:summary.get(eid,{}).get(arm,{}).get('score') for arm in lock['arms']};scores.update(probe=orig.get(eid,{}).get('probe_score'),jview=orig.get(eid,{}).get('jlens_score'),context_only=context.get(eid,{}).get('context_only_score'));rows.append({'episode_id':eid,'family_id':r['family_id'],'label':1 if r['label']=='misaligned' else 0 if r['label']=='benign' else None,'original_label':r['label'],'scores':scores})
 known=[r for r in rows if r['label'] is not None];report={'dataset':a.dataset,'offset':a.offset,'requested':len(rows),'known_labels':len(known),'uncertain_or_unavailable_labels':len(rows)-len(known),'thresholds':thresholds,'metrics':{},'paired_comparisons':{},'scope':'Frozen original GPT-OSS checkpoint, authored task families, automated readers; retrospective display extension. Provider transport differences remain a limitation. No causal necessity or universal coverage claim.','lock_sha256':digest(lp)}
 for arm in arms:
  usable=[r for r in known if r['scores'][arm] is not None];m=operating_point([r['label'] for r in usable],[r['scores'][arm] for r in usable],thresholds[arm]);m['missing_known']=len(known)-len(usable);m['available_all_labels']=sum(r['scores'][arm] is not None for r in rows)
  missingpos=sum(r['label']==1 and r['scores'][arm] is None for r in known);missingneg=sum(r['label']==0 and r['scores'][arm] is None for r in known);pos=sum(r['label']==1 for r in known);neg=len(known)-pos;m['missingness_tpr_bounds']=[m['tp']/pos,(m['tp']+missingpos)/pos] if pos else None;m['missingness_fpr_bounds']=[m['fp']/neg,(m['fp']+missingneg)/neg] if neg else None;report['metrics'][arm]=m
 for arm in lock['arms']:
  for comparator in ['probe','jview','context_only']:
   paired=[r for r in known if r['scores'][arm] is not None and r['scores'][comparator] is not None];y=[r['label'] for r in paired];aa=[r['scores'][arm] for r in paired];bb=[r['scores'][comparator] for r in paired];groups=[r['family_id'] for r in paired]
   result={'paired_n':len(paired),'table':disagreement_table(y,{arm:[s>=thresholds[arm] for s in aa],comparator:[s>=thresholds[comparator] for s in bb]})}
   if len(set(groups))>=2:result['bootstrap']=paired_cluster_difference(y,aa,bb,groups,thresholds[arm],thresholds[comparator],seed=20260916)
   if comparator=='probe':result['matched_validation_specificity_probe']=operating_point(y,bb,lock['arms'][arm]['matched_probe_threshold'])
   report['paired_comparisons'][arm+' minus '+comparator]=result
 # Direct summary-versus-shuffled contrast, no equivalence claim from a wide CI.
 paired=[r for r in known if r['scores']['jsummary'] is not None and r['scores']['jsummary_shuffled'] is not None]
 if len({r['family_id'] for r in paired})>=2:report['summary_minus_shuffled']=paired_cluster_difference([r['label'] for r in paired],[r['scores']['jsummary'] for r in paired],[r['scores']['jsummary_shuffled'] for r in paired],[r['family_id'] for r in paired],thresholds['jsummary'],thresholds['jsummary_shuffled'],seed=20260916)
 # Treat uncertain labels as benign only in the explicitly named sensitivity panel.
 sensitivity=[r for r in rows if r['original_label'] in ['misaligned','benign','uncertain']];report['uncertain_as_benign']={}
 for arm in arms:
  usable=[r for r in sensitivity if r['scores'][arm] is not None];report['uncertain_as_benign'][arm]=operating_point([int(r['label']==1) for r in usable],[r['scores'][arm] for r in usable],thresholds[arm])
 casebook=[]
 for label in [0,1]:
  cells={}
  for r in known:
   if r['label']!=label or any(r['scores'][arm] is None for arm in ['jsummary','probe','jview','context_only']):continue
   pattern=tuple(arm for arm in ['jsummary','probe','jview','context_only'] if r['scores'][arm]>=thresholds[arm]);cells.setdefault(pattern,[]).append(r['episode_id'])
  for pattern,ids in cells.items():casebook.append({'label':label,'flags':pattern,'ids':sorted(ids,key=lambda x:hashlib.sha256(x.encode()).hexdigest())[:3]})
 report['casebook_selection']=casebook;out=ROOT/f'reports/jsummary-{stem}';out.mkdir(parents=True,exist_ok=True);write_json(out/'summary.json',report);write_json(out/'cases.json',rows);print(json.dumps({'dataset':a.dataset,'offset':a.offset,'metrics':report['metrics']}),flush=True)
if __name__=='__main__':main()
