"""Offline completion-triggered receipt, aggregation and frozen-lock audit."""
import argparse,json,math,time
from pathlib import Path
from contracts import fingerprint,parse_json_reply
from smoke import digest,write_json
from legacy_control_reviews import payload,valid
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');a=p.parse_args();run=ROOT/'runs/reader-comparison/legacy-specificity-reviews';deadline=time.monotonic()+3600
 while not (run/'complete.json').exists():
  if not a.wait or time.monotonic()>deadline:raise RuntimeError('Terminal evaluated reviews required')
  time.sleep(1)
 reg=json.loads((run/'registration.json').read_text());done=json.loads((run/'complete.json').read_text());ledger=json.loads((ROOT.parent/'reader-runtime/openrouter-budget.json').read_text());sources={}
 for path,h in {**reg['source_hashes'],**done['source_hashes']}.items():
  if digest(path)!=h:raise ValueError('Changed registered input or evaluated output')
  sources[path]=h
 if reg['code_sha256']!=digest(Path(__file__).with_name('legacy_control_reviews.py')):raise ValueError('Coordinator changed during execution')
 cache=ROOT/'runs/jsummary-api-cache';usable={};missing={};total=0
 for key,request in reg['pending'].items():
  if fingerprint(request)!=key:raise ValueError('Registration request hash mismatch')
  results=cache/(key+'.json');raws=list(cache.glob(key+'-raw-*.json'));records=[r for r in ledger['records'].values() if r['request_sha256']==key]
  if len(records)!=1:raise ValueError('Exactly one attempt required')
  record=records[0]
  if results.exists():
   if len(raws)!=1:raise ValueError('Exactly one raw receipt required')
   raw=json.loads(raws[0].read_text());response=raw['response'];result=json.loads(results.read_text())
   assert raw['request']==request and result['request']==request and result['request_sha256']==key
   assert response['model']==request['model'] and response['choices'][0]['finish_reason']=='stop'
   assert parse_json_reply(response['choices'][0]['message']['content'])==result['judgment'] and valid(result)
   assert record==ledger['records'][raw['budget_reservation']] and record['status']=='settled' and record['response_id']==response['id']
   assert record['actual_microusd']==math.ceil(float(response['usage']['cost'])*1e6)
   usable[key]=result
   for f in [results,raws[0]]:sources[str(f)]=digest(f)
  else:
   assert key in done['missing'];missing[key]={'error':done['missing'][key],'ledger_status':record['status'],'raw_receipts':len(raws)}
   assert record['status'] in ['reserved','settled']
   for f in raws:sources[str(f)]=digest(f)
  if record['status']=='settled':total+=record['actual_microusd']
 for key in reg['cached']:
  f=cache/(key+'.json');usable[key]=json.loads(f.read_text());sources[str(f)]=digest(f)
 reports={}
 for panel in done['panels']:
  prep=ROOT/f'runs/reader-comparison/legacy-specificity-review-preparation/{panel}.json';cohort=json.loads(prep.read_text());target=ROOT/f'runs/{panel}-jsummary-test';actual=json.loads((target/'scores.json').read_text());byid={r['episode_id']:r for r in actual}
  for row in actual:
   for arm in ['jsummary','jsummary_plus_tokens','jsummary_blind','jview_blind','jsummary_shuffled']:
    pair=[j for j in cohort['jobs'] if j['episode_id']==row['episode_id'] and j['arm']==arm];results=[usable.get(fingerprint(payload(j))) for j in pair]
    expected=None if len(results)!=2 or any(r is None for r in results) else min(r['judgment']['score'] for r in results)
    assert row[arm]['score']==expected
  rp=ROOT/f'reports/jsummary-{panel}/summary.json';reports[panel]=json.loads(rp.read_text());assert reports[panel]['lock_sha256']==digest(ROOT/'runs/fresh-jsummary-calibration/lock.json')
  for f in [prep,target/'scores.json',target/'review-complete.json',rp]:sources[str(f)]=digest(f)
 for f in [run/'registration.json',run/'complete.json',Path(__file__)]:sources[str(f)]=digest(f)
 out=ROOT/'studies/reader_comparison/evidence/legacy-specificity-review-audit.json'
 if out.exists():raise ValueError('Preserve completed audit')
 write_json(out,{'source_hashes':sources,'verified_unique_usable':len(usable),'unavailable':missing,'settled_review_microusd':total,'panels':{k:{'requested':v['requested'],'known_labels':v['known_labels'],'metrics':v['metrics']} for k,v in reports.items()},'scope':'All available new review receipts and registered aggregation matched; unavailable outputs and charges preserved. Original calibration lock unchanged. This audit verifies provenance and arithmetic, not semantic ground truth.'})
 sections=['# Legacy specificity control results','The original GPT OSS authorization and monitor maintenance panels were evaluated with frozen summary thresholds and original review payloads. These results are separate from the Qwen Oracle comparison. They are retrospective specificity controls, not a new confirmatory test of broad misalignment detection.']
 for panel,r in reports.items():
  sections+=['## '+panel,f"Requested {r['requested']} episodes; {r['known_labels']} have known labels. Uncertain labels remain excluded from the primary rates and are included only in the existing sensitivity analysis."]
  table=['| Arm | TP / positive | FP / benign | Missing known |','|---|---:|---:|---:|']
  for arm,m in r['metrics'].items():table.append(f"| {arm} | {m['tp']}/{m['tp']+m['fn']} | {m['fp']}/{m['fp']+m['tn']} | {m['missing_known']} |")
  sections+=['\n'.join(table)]
 sections+=['## Interpretation boundary','Zero false positives in a finite control panel do not establish zero population risk. Any unavailable output remains unknown, not benign. Full family uncertainty and uncertain-as-benign sensitivity analyses remain in each original evaluation JSON. Template challenge and incomplete code-onset coverage remain separate outstanding requirements.']
 (ROOT/'reports/reader-comparison/legacy-specificity-results.md').write_text('\n\n'.join(sections)+'\n');print(json.dumps({'verified_unique':len(usable),'missing':len(missing),'settled_review_usd':total/1e6,'panels':list(reports)}),flush=True)
if __name__=='__main__':main()
