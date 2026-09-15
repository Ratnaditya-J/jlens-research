"""Post-hoc paired J-view/context analysis at frozen endpoint thresholds."""
import collections,hashlib,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];inputs={};results=[]
def read(p):
 p=ROOT/p;inputs[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
for offset in (0,32,64):
 suffix=f'-offset{offset}' if offset else '';cases=read(Path(f'reports/final-comparison{suffix}/cases.json'));baseline={r['episode_id']:r for r in read(Path(f'reports/final-comparison{suffix}/baseline-cases.json'))};lock=read(Path(f'runs/fresh{suffix}-calibration/lock.json'));rows=[];missing_context=[]
 for c in cases:
  score=baseline[c['episode_id']]['context_only_score']
  if c['category'] is not None and c['behavior_label'] in ('misaligned','benign') and score is None:missing_context.append(c['episode_id'])
  if c['category'] is None or c['behavior_label'] not in ('misaligned','benign') or score is None:continue
  context=score>=lock['context_only_threshold'];j=c['jlens_flag'];category='both' if j and context else 'jview_only' if j else 'context_only' if context else 'neither'
  rows.append({'episode_id':c['episode_id'],'family':c['task_group'],'label':c['behavior_label'],'jview':j,'context':context,'probe':c['probe_flag'],'jview_vs_context':category})
 strata={label:dict(collections.Counter(r['jview_vs_context'] for r in rows if r['label']==label)) for label in ('misaligned','benign')}
 unique=[r for r in rows if r['label']=='misaligned' and r['jview'] and not r['probe']]
 groups=sorted({r['family'] for r in rows});rng=random.Random(20260918);samples={label:[] for label in ('misaligned','benign')}
 for _ in range(2000):
  selected=rng.choices(groups,k=len(groups));rr=[r for g in selected for r in rows if r['family']==g]
  for label in samples:
   ss=[r for r in rr if r['label']==label]
   if ss:samples[label].append(sum(int(r['jview'])-int(r['context']) for r in ss)/len(ss))
 intervals={}
 for label,v in samples.items():
  v.sort();intervals[label]=[v[int(.025*(len(v)-1))],v[int(.975*(len(v)-1))]] if v else None
 results.append({'offset':offset,'known_paired':len(rows),'missing_context_on_known_probe_j_pairs':missing_context,'counts':strata,'jview_only_vs_probe_positive_cases':len(unique),'of_these_context_also_flags':sum(r['context'] for r in unique),'jview_minus_context_rate_intervals':intervals,'rows':rows})
report={'scope':'Post-hoc diagnostic, using existing independently frozen J-view and context-only thresholds. Describes incremental flags on the same cases, not a causal proof of internal-information necessity or matched-FPR superiority.','bootstrap':'2000 whole-family resamples; seed20260918; empirical 2.5/97.5 percentiles. Few families and zero discordances limit inference.','results':results,'inputs_sha256':inputs}
(ROOT/'reports/jview-context-increment.json').write_text(json.dumps(report,indent=2)+'\n')
for r in results:print(json.dumps({k:v for k,v in r.items() if k!='rows'}))
