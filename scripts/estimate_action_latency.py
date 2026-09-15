"""Offline, conditional timing margins for audited casebook statements, both detectors."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
inputs={}
def read(p):
 p=ROOT/p;inputs[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
probe=read(Path('reports/probe-latency-primary.json'))['warm_single_activation_score_seconds']['p95']
rows=[]
for offset in (0,32,64):
 suffix=f'-offset{offset}' if offset else ''
 audit=read(Path(f'reports/final-comparison{suffix}/action-audit.json'))
 for a in audit['rows']:
  eid=a['episode_id'];row={'episode_id':eid,'offset':offset,'behavior_label':a['behavior_label']}
  if 'localized_statement_sample_index' not in a or not a['observables_match_original_audit']:
   rows.append({**row,'unavailable':'No verified behavior-preserving statement localization'});continue
  ep=read(Path('runs/fresh')/eid/'episode.json');assert inputs[str(Path('runs/fresh')/eid/'episode.json')]==a['episode_sha256']
  start=a.get('scored_sample_index',a.get('code_onset_sample_index'));end=a['localized_statement_sample_index'];steps=ep['step_seconds']
  assert 0<=start<end<len(steps)
  gap=sum(steps[start+1:end])
  timing_paths=list(ROOT.glob(f'runs/fresh-processed-*/{eid}/timings.json'));assert len(timing_paths)==1
  timing=read(timing_paths[0].relative_to(ROOT));t=next(x for x in timing['positions'] if x['offset']==offset)
  reviews=[read(Path(f'runs/fresh{suffix}-jview-test/reviews')/eid/f'jview-{model}.json') for model in ('gpt-4.1-2025-04-14','gpt-5.4')]
  # Ideal simultaneous requests: max wall duration; queuing and transport-to-review scheduling excluded.
  jl=t['display_seconds']+max(r['elapsed_seconds'] for r in reviews)
  row.update(scored_sample_index=start,localized_statement_sample_index=end,intervening_recorded_generation_seconds=gap,probe_warm_p95_seconds=probe,jlens_display_plus_parallel_review_seconds=jl)
  for name,cost in [('probe',probe),('jlens',jl)]:
   flag=a.get(name+'_flag_at_scored_position',a.get(name+'_flag_at_code_onset'))
   row[name]={'flag':flag,'conditional_resident_activation_margin_seconds':gap-cost if flag else None,'conditional_replay_margin_seconds':gap-cost-t['replay_seconds'] if flag else None}
  rows.append(row)
summary={}
for offset in (0,32,64):
 valid=[r for r in rows if r['offset']==offset and 'unavailable' not in r]
 summary[str(offset)]={'localized_cases':len(valid),'detectors':{name:{'flagged':sum(bool(r[name]['flag']) for r in valid),'positive_resident_margin':sum(r[name]['conditional_resident_activation_margin_seconds'] is not None and r[name]['conditional_resident_activation_margin_seconds']>0 for r in valid),'positive_replay_margin':sum(r[name]['conditional_replay_margin_seconds'] is not None and r[name]['conditional_replay_margin_seconds']>0 for r in valid)} for name in ('probe','jlens')}}
report={'scope':'Offline latency-adjusted scenario estimates on selected localized casebook cases; not measured online detector warning times','generation_gap_definition':'Sum step_seconds[start+1:end], excluding scored and statement token steps. Conservative gap between completed scored step and beginning statement-token forward pass. Statement location is code generation, not actual execution or mental commitment.','assumptions':['Warm resident weights/activation; probe primary p95 microbenchmark reused for earlier linear probes, not independently measured there.','J display plus maximum of two recorded API request times assumes simultaneous launch; no queue, transfer, scheduling or runtime contention included.','Replay margin additionally subtracts measured replay time; neither scenario is end-to-end deployment validation.','Selected casebook is not representative. No inference of earliest detection from sampled endpoints. Missing localization is excluded, not a failure or success.'],'summary':summary,'rows':rows,'inputs':inputs}
(ROOT/'reports/action-latency-scenarios.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary,indent=2))
