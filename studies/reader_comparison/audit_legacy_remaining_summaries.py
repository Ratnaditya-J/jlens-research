"""Offline exact-payload receipt and frozen-input audit; never dispatch inference."""
import json,math
from pathlib import Path
from contracts import fingerprint,parse_json_reply
from smoke import digest,write_json
ROOT=Path(__file__).resolve().parents[2]
def main():
 run=ROOT/'runs/reader-comparison/legacy-remaining-summaries';reg=json.loads((run/'registration.json').read_text());done=json.loads((run/'complete.json').read_text())
 assert done['usable_unique']==472 and not done['unavailable']
 ledger=json.loads((ROOT.parent/'reader-runtime/openrouter-budget.json').read_text());cache=ROOT/'runs/jsummary-api-cache';sources={};total=0
 for p,h in reg['source_hashes'].items():
  assert digest(p)==h;sources[p]=h
 runner=Path(__file__).with_name('legacy_remaining_summaries.py');assert digest(runner)==reg['code_sha256'];sources[str(runner)]=digest(runner)
 for key,request in reg['jobs'].items():
  assert fingerprint(request)==key
  raws=list(cache.glob(key+'-raw-*.json'));assert len(raws)==1
  raw=json.loads(raws[0].read_text());resultpath=cache/(key+'.json');result=json.loads(resultpath.read_text());response=raw['response'];record=ledger['records'][raw['budget_reservation']]
  assert raw['request']==request==result['request'] and result['request_sha256']==key
  assert response['model']==request['model'] and response['choices'][0]['finish_reason']=='stop'
  assert parse_json_reply(response['choices'][0]['message']['content'])==result['judgment']
  assert isinstance(result['judgment']['interpretation'],str) and result['judgment']['interpretation'].strip()
  assert record['status']=='settled' and record['response_id']==response['id'] and record['request_sha256']==key
  assert record['actual_microusd']==math.ceil(float(response['usage']['cost'])*1e6)
  total+=record['actual_microusd']
  for p in [raws[0],resultpath]:sources[str(p)]=digest(p)
 for panel,aliases in reg['aliases'].items():
  target=ROOT/f'runs/{panel}-jsummary-test';rows=json.loads((target/'summaries.json').read_text());bykey={(r['episode_id'],r['layer']):r for r in rows};assert len(rows)==len(aliases)
  for alias in aliases:
   row=bykey[alias['episode_id'],alias['layer']];assert row['request_sha256']==alias['key']
   assert row['interpretation']==json.loads((cache/(alias['key']+'.json')).read_text())['judgment']['interpretation']
  for name in ['summaries.json','summary-manifest.json','summary-complete.json']:sources[str(target/name)]=digest(target/name)
 launch=ROOT/'studies/reader_comparison/evidence/legacy-remaining-launch.json'
 for p,h in json.loads(launch.read_text())['source_hashes'].items():assert digest(p)==h;sources[p]=h
 for p in [launch,run/'registration.json',run/'complete.json',Path(__file__)]:sources[str(p)]=digest(p)
 report={'verified_unique':len(reg['jobs']),'settled_summary_microusd':total,'source_hashes':sources,'scope':'Exact template summaries, raw receipts and ledger settlements verified; frozen originals and original partial code-onset output unchanged. Arithmetic/provenance audit, not semantic validation.'}
 out=ROOT/'studies/reader_comparison/evidence/legacy-remaining-summary-audit.json';assert not out.exists();write_json(out,report)
 print(json.dumps({'verified_unique':report['verified_unique'],'settled_summary_usd':total/1e6}))
if __name__=='__main__':main()
