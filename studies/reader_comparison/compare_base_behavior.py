"""Descriptive training-only adapter effect; never alter detector evaluation."""
import argparse,json,random
from pathlib import Path
from smoke import digest,write_json
from contracts import fingerprint
def compare(base,subject):
 pairs=[]
 for b in base:
  if b['split']!='train':raise ValueError('This control is training-only')
  s=subject[b['episode_id']]
  if s['family_id']!=b['family_id'] or s['condition']!=b['condition']:raise ValueError('Pair identity mismatch')
  pairs.append((b,s))
 report={}
 for condition in ['prohibited','authorized']:
  subset=[(b,s) for b,s in pairs if b['condition']==condition];usable=[(b,s) for b,s in subset if b['status']=='ok' and s['status']=='ok'];families=sorted({b['family_id'] for b,s in usable});metric=(lambda r:r['label']) if condition=='prohibited' else (lambda r:int(r['state']['named_action_executed']))
  grouped={f:[metric(s)-metric(b) for b,s in usable if b['family_id']==f] for f in families};differences=[];rng=random.Random(20260926)
  for _ in range(2000):
   values=[v for f in rng.choices(families,k=len(families)) for v in grouped[f]] if families else []
   if values:differences.append(sum(values)/len(values))
  differences.sort();report[condition]={'requested_pairs':len(subset),'usable_pairs':len(usable),'base_invalid':sum(b['status']!='ok' for b,s in subset),'subject_invalid':sum(s['status']!='ok' for b,s in subset),'base_count':sum(metric(b) for b,s in usable),'subject_count':sum(metric(s) for b,s in usable),'metric':'policy_violation' if condition=='prohibited' else 'authorized_action_execution','subject_minus_base_rate':sum(metric(s)-metric(b) for b,s in usable)/len(usable) if usable else None,'family_bootstrap_95ci':[differences[int(.025*(len(differences)-1))],differences[int(.975*(len(differences)-1))]] if differences else None,'families':len(families),'family_differences':{f:sum(v)/len(v) for f,v in grouped.items()}}
 return report
def main():
 p=argparse.ArgumentParser();p.add_argument('--base-audits',type=Path,required=True);p.add_argument('--subject-audits',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--base-episodes',type=Path,required=True);p.add_argument('--subject-episodes',type=Path,required=True);a=p.parse_args();b=json.loads(a.base_audits.read_text());s={r['episode_id']:r for r in json.loads(a.subject_audits.read_text())}
 for r in b:
  eid=r['episode_id'];be=json.loads((a.base_episodes/(eid+'.json')).read_text());se=json.loads((a.subject_episodes/(eid+'.json')).read_text())
  if fingerprint(be)!=r['episode_sha256'] or fingerprint(se)!=s[eid]['episode_sha256']:raise ValueError('Audit episode mismatch')
  if any(be[k]!=se[k] for k in ['messages','prompt_ids','seed']):raise ValueError('Prompt/seed pair changed')
  if be['identity']['adapter_enabled'] or not se['identity']['adapter_enabled'] or dict(be['identity'],adapter_enabled=True)!=se['identity']:raise ValueError('Base/subject execution identity mismatch')
 report={'panels':compare(b,s),'base_audit_sha256':digest(a.base_audits),'subject_audit_sha256':digest(a.subject_audits),'scope':'Training-only descriptive base-versus-adapter behavioral comparison using the same prompts and sampling seeds. Eight task families give limited uncertainty resolution. A shared seed does not hold sampled tokens constant once model distributions diverge. No latent-intent or general emergent-misalignment claim; no detector selection uses this control.'};a.out.parent.mkdir(parents=True,exist_ok=True);write_json(a.out,report);print(json.dumps(report['panels']))
if __name__=='__main__':main()
