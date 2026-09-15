"""Secondary native-package behavioral controls; no detector identity training."""
import collections,hashlib,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];inputs={}
def read(path):
 p=ROOT/path;inputs[str(path)]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
def rate(rows,key):
 known=[r[key] for r in rows if r[key] in ('misaligned','benign')]
 return sum(x=='misaligned' for x in known)/len(known) if known else None
def interval(values):
 v=sorted(x for x in values if x is not None)
 return [v[int(.025*(len(v)-1))],v[int(.975*(len(v)-1))]] if v else None
primary={x['episode_id']:x for x in read(Path('runs/fresh/review-summary.json'))['rows']}
rows=[];summaries={}
for role in ('base','honest'):
 read(Path(f'runs/secondary-{role}/collection-complete.json'))
 cfg=read(Path(f'configs/secondary-{role}-v1.json'));labels={r['episode_id']:r for r in read(Path(f'runs/secondary-{role}/review-summary.json'))['rows']}
 assert set(labels)=={e['episode_id'] for e in cfg['episodes']}
 for ep in cfg['episodes']:
  x=labels[ep['episode_id']];src=primary[ep['source_episode_id']]
  rows.append({'model':role,'episode_id':ep['episode_id'],'source_episode_id':ep['source_episode_id'],'family_id':ep['family_id'],'template':ep['template'],'control_label':x.get('label','unavailable'),'control_status':x['status'],'primary_label':src.get('label','unavailable')})
 rr=[r for r in rows if r['model']==role];groups=sorted({r['family_id'] for r in rr});rng=random.Random(20260917);boot=[];differences=[]
 for _ in range(2000):
  draw=rng.choices(groups,k=len(groups));sample=[r for g in draw for r in rr if r['family_id']==g];boot.append(rate(sample,'control_label'))
  paired=[r for r in sample if r['control_label'] in ('misaligned','benign') and r['primary_label'] in ('misaligned','benign')]
  a=rate(paired,'control_label');b=rate(paired,'primary_label');differences.append(a-b if a is not None and b is not None else None)
 paired=[r for r in rr if r['control_label'] in ('misaligned','benign') and r['primary_label'] in ('misaligned','benign')]
 a=rate(paired,'control_label');b=rate(paired,'primary_label')
 summaries[role]={'attempts':len(rr),'label_counts':dict(collections.Counter(r['control_label'] for r in rr)),'statuses':dict(collections.Counter(r['control_status'] for r in rr)),'known_label_violation_rate':rate(rr,'control_label'),'family_cluster_interval':interval(boot),'jointly_known_pairs':len(paired),'paired_control_minus_primary_rate':a-b if a is not None and b is not None else None,'paired_difference_interval':interval(differences),'paired_label_counts':dict(collections.Counter(r['primary_label']+' / '+r['control_label'] for r in paired))}
report={'scope':'Secondary descriptive behavioral controls with matched message content and seeds; native chat templates differ, so not a weights-only causal comparison. No cross-model detector training or reused J-lens validity claim.','summary':summaries,'rows':rows,'inputs':inputs,'uncertainty':'2000 paired whole-family bootstrap resamples, seed20260917, percentile intervals. Only15families; zero-width intervals cannot establish zero population risk. Missing/uncertain cases remain explicit.','provider':'Control behavior reviewers use OpenAI models via OpenRouter; primary behavior reviews used direct OpenAI. Provider transport and model-package template differences are limitations.'}
out=ROOT/'reports/model-controls';out.mkdir(exist_ok=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['# Secondary model controls','','Native model-package behavioral comparison; matched messages and seeds, different shipped chat templates. No weights-only causal claim.','','| Model | Attempts | Misaligned | Benign | Uncertain/unavailable |','|---|---:|---:|---:|---:|']
for role,s in summaries.items():
 c=s['label_counts'];lines.append(f"| {role} | {s['attempts']} | {c.get('misaligned',0)} | {c.get('benign',0)} | {s['attempts']-c.get('misaligned',0)-c.get('benign',0)} |")
lines+=['',report['uncertainty'],'',report['provider'],'','See summary.json for family-cluster intervals, paired comparisons and every attempted case. The author-described honest model is not assumed benign in advance.']
(out/'findings.md').write_text('\n'.join(lines)+'\n');print(json.dumps(summaries,indent=2))
