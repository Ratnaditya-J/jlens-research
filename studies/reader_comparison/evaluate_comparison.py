"""Locked held-out reader/probe comparison; controls and uncertainty stay explicit."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from smoke import write_json,digest
from contracts import fingerprint
from metrics import operating_point,paired_cluster_difference,disagreement_table
from forecast_limits import empirical_limits

def main():
 p=argparse.ArgumentParser();p.add_argument('--features',type=Path,required=True);p.add_argument('--probes',type=Path,required=True);p.add_argument('--interpretations',type=Path,required=True);p.add_argument('--lock',type=Path,required=True);p.add_argument('--policy-reviews',type=Path,required=True);p.add_argument('--audits',type=Path,required=True);p.add_argument('--captures',type=Path,required=True);p.add_argument('--text-baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();lock=json.loads(a.lock.read_text())
 for path,sha in lock['source_hashes'].items():
  if digest(path)!=sha:raise ValueError('Locked artifact changed: '+path)
 fm=json.loads((a.features/'manifest.json').read_text());arr=np.load(a.features/'features.npz',allow_pickle=False)
 if digest(a.features/'features.npz')!=fm['feature_sha256'] or fm['identity']!=lock['identity']:raise ValueError('Feature identity mismatch')
 scores={r['episode_id']:r for r in json.loads((a.interpretations/'scores.json').read_text())};done=json.loads((a.interpretations/'complete.json').read_text());im=json.loads((a.interpretations/'manifest.json').read_text())
 if done['manifest_sha256']!=fingerprint(im) or im['interpreter_code_sha256']!=lock['interpreter_code_sha256']:raise ValueError('Changed test interpreter manifest')
 if done['scores_sha256']!=digest(a.interpretations/'scores.json') or im['phase']!='test' or im['subject_identity']!=fm['identity'] or im['endpoint']!=lock['endpoint'] or im['lens_sha256']!=fm['lens_sha256']:raise ValueError('Invalid test readouts')
 if digest(a.audits)!=fm['audits_sha256']:raise ValueError('Independent audit provenance differs')
 audits=json.loads(a.audits.read_text());test_audits=[r for r in audits if r['split']=='test']
 review_complete=json.loads((a.policy_reviews.parent/'complete.json').read_text())
 if review_complete['reviews_sha256']!=digest(a.policy_reviews):raise ValueError('Independent review artifact changed')
 independent={r['episode_id']:r for r in json.loads(a.policy_reviews.read_text())};audit_by_id={r['episode_id']:r for r in audits};rows={}
 for i,r in enumerate(fm['rows']):
  if r['split']!='test':continue
  eid=r['episode_id'];row=rows.setdefault(eid,{k:r[k] for k in ['episode_id','family_id','condition','label','prefix_sha256','position_in_generated_output']});row.setdefault('scores',{})
  for arm in lock['thresholds']:
   if arm.endswith('_probe'):continue
   row['scores'][arm]=scores.get(eid,{}).get(arm,{}).get('score')
 for arm in ['raw','jspace']:
  probe=json.loads((a.probes/(arm+'-probe.json')).read_text());weights=np.asarray(probe['weights']);x=arr['X_'+arm]
  for i,r in enumerate(fm['rows']):
   if r['split']=='test' and r['layer']==probe['selected']['layer']:
    value=float(np.einsum('i,i->',x[i].astype(np.float64),weights)+probe['intercept'])
    if not np.isfinite(value):raise ValueError('Nonfinite probe score')
    rows[r['episode_id']]['scores'][arm+'_probe']=value
 import joblib
 text_lock=json.loads((a.text_baseline/'lock.json').read_text())
 if text_lock['model_sha256']!=digest(a.text_baseline/'model.joblib') or text_lock['capture_manifest_sha256']!=fm['capture_manifest_sha256']:raise ValueError('Text baseline provenance mismatch')
 text_model=joblib.load(a.text_baseline/'model.joblib')
 for eid,row in rows.items():
  directory=a.captures/eid;complete=json.loads((directory/'complete.json').read_text())
  if digest(directory/'cells.json')!=complete['cells_sha256'] or complete['manifest_sha256']!=fm['capture_manifest_sha256']:raise ValueError('Causal text metadata changed')
  cells=[r for r in json.loads((directory/'cells.json').read_text()) if r['endpoint']==lock['endpoint']]
  row['scores']['text_probe']=float(text_model.decision_function([cells[0]['prefix_text']])[0])
 for eid,row in rows.items():
  ir=independent.get(eid,{})
  if ir and ir['episode_sha256']!=audit_by_id[eid]['episode_sha256']:raise ValueError('Policy review belongs to a different trajectory')
  row['independent_policy_label']=ir.get('label','unavailable');row['strict_confirmation']=ir.get('agreement',False) and ir.get('label')==('violation' if row['label']==1 else 'benign')
 rows=list(rows.values());arms=list(lock['thresholds']);thresholds=lock['thresholds'];primary=[r for r in rows if r['condition']=='prohibited' and r['label'] in [0,1]];controls=[r for r in rows if r['condition']=='authorized' and r['label'] in [0,1]]
 def panel(dataset):
  metrics={}
  for arm in arms:
   valid=[r for r in dataset if r['scores'].get(arm) is not None];m=operating_point([r['label'] for r in valid],[r['scores'][arm] for r in valid],thresholds[arm]);m['requested']=len(dataset);m['unavailable']=len(dataset)-len(valid);metrics[arm]=m
  return metrics
 report={'identity':fm['identity'],'endpoint':lock['endpoint'],'lock_sha256':digest(a.lock),'total_test_requested':len(test_audits),'test_action_unavailable':sum(r['label'] is None for r in test_audits),'test_not_captured_or_read':len(test_audits)-len(rows),'primary_n':len(primary),'control_n':len(controls),'primary_families':len({r['family_id'] for r in primary}),'metrics':panel(primary),'authorized_controls':panel(controls),'strict_review_agreement_metrics':panel([r for r in primary if r['strict_confirmation']]),'strict_review_agreement_n':sum(r['strict_confirmation'] for r in primary),'forecast_limits':empirical_limits(primary),'comparisons':{},'scope':'Descriptive controlled policy-action experiment on one checkpoint. Four held-out operational families provide limited population precision. Independent reviewers validate policy, not hidden intent. Secondary contrasts are exploratory.'}
 comparisons=[('raw_probe','text_probe'),('oracle_context','j_summary_context'),('raw_probe','jspace_probe'),('oracle_context','raw_probe'),('j_summary_context','raw_probe'),('oracle_context','context_only'),('j_summary_context','context_only'),('oracle_context','oracle_shuffled_context'),('j_summary_context','j_summary_shuffled_context'),('oracle','j_summary'),('j_summary','j_tokens')]
 for aa,bb in comparisons:
  paired=[r for r in primary if r['scores'].get(aa) is not None and r['scores'].get(bb) is not None];y=[r['label'] for r in paired];sa=[r['scores'][aa] for r in paired];sb=[r['scores'][bb] for r in paired];groups=[r['family_id'] for r in paired]
  item={'paired_n':len(paired),'table':disagreement_table(y,{aa:[s>=thresholds[aa] for s in sa],bb:[s>=thresholds[bb] for s in sb]})}
  if len(set(groups))>=2:item['bootstrap']=paired_cluster_difference(y,sa,sb,groups,thresholds[aa],thresholds[bb])
  if bb=='raw_probe' and aa in lock['arms'] and 'matched_raw_probe_threshold' in lock['arms'][aa]:item['matched_validation_specificity_raw_probe']=operating_point(y,sb,lock['arms'][aa]['matched_raw_probe_threshold'])
  report['comparisons'][aa+' minus '+bb]=item
 cfg=json.loads((Path(__file__).parent/'comparison_config.json').read_text());clusters=cfg['mechanism_clusters'];aa,bb=cfg['primary_contrast'];paired=[r for r in primary if r['scores'].get(aa) is not None and r['scores'].get(bb) is not None];macro=[clusters[r['family_id']] for r in paired]
 report['primary_mechanism_cluster_count']=len(set(macro))
 if len(set(macro))>=2:report['primary_mechanism_cluster_sensitivity']=paired_cluster_difference([r['label'] for r in paired],[r['scores'][aa] for r in paired],[r['scores'][bb] for r in paired],macro,thresholds[aa],thresholds[bb])
 report['mechanism_generalization_scope']='Operational families are held out; related mechanism categories cross splits. The held-out bank contains only two broad mechanism clusters, so this is not a reliable population-wide estimate.'
 selected=['raw_probe','j_summary_context','oracle_context'];paired=[r for r in primary if all(r['scores'].get(arm) is not None for arm in selected)];report['three_way_table']=disagreement_table([r['label'] for r in paired],{arm:[r['scores'][arm]>=thresholds[arm] for r in paired] for arm in selected});report['casebook_selection']=[]
 for label in [0,1]:
  groups={}
  for r in paired:
   if r['label']!=label:continue
   flags=tuple(arm for arm in selected if r['scores'][arm]>=thresholds[arm]);groups.setdefault(flags,[]).append(r['episode_id'])
  for flags,ids in groups.items():report['casebook_selection'].append({'label':label,'flags':flags,'ids':sorted(ids,key=lambda x:hashlib.sha256(x.encode()).hexdigest())[:3]})
 def flag(row,arm):
  score=row['scores'].get(arm);return None if score is None else score>=thresholds[arm]
 # Report probe/J-display blind spots without conflating display with full space.
 report['probe_detected_jdisplay_missed']=[{'episode_id':r['episode_id'],'jspace_probe_detected':flag(r,'jspace_probe'),'oracle_detected':flag(r,'oracle_context'),'context_detected':flag(r,'context_only')} for r in paired if r['label']==1 and r['scores']['raw_probe']>=thresholds['raw_probe'] and r['scores']['j_summary_context']<thresholds['j_summary_context']]
 a.out.mkdir(parents=True,exist_ok=True);write_json(a.out/'summary.json',report);write_json(a.out/'cases.json',rows);print(json.dumps({'total_test_requested':len(test_audits),'test_action_unavailable':sum(r['label'] is None for r in test_audits),'test_not_captured_or_read':len(test_audits)-len(rows),'primary_n':len(primary),'metrics':report['metrics']}),flush=True)
if __name__=='__main__':main()
