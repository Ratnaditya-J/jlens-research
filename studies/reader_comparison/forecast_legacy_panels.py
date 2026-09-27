"""Offline receipt-based planning for frozen legacy panels; never dispatches."""
import json,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 cfg=json.loads((ROOT/'configs/jsummary-v1.json').read_text()); costs=collections.defaultdict(list);receipts=[]
 for p in (ROOT/'runs/jsummary-api-cache').glob('*.json'):
  if '-raw-' in p.name:continue
  try:d=json.loads(p.read_text())
  except (ValueError,OSError):continue
  if not isinstance(d,dict):continue
  v=(d.get('usage') or {}).get('cost');model=d.get('requested_model')
  if model in [cfg['summarizer_model'],*cfg['reviewers']] and isinstance(v,(int,float)):
   costs[model].append(v);receipts.append((p.name,sha(p)))
 means={m:sum(v)/len(v) for m,v in costs.items()};panels={};sources={}
 for panel in ['specificity-controls','monitor-controls','template-challenge']:
  p=ROOT/f'runs/{panel}-assembled/test-readouts.json';rows=json.loads(p.read_text());sources[str(p)]=sha(p);n=len(rows);cells=sum(len(r['layers']) for r in rows)
  panels[panel]={'episodes':n,'summary_cell_slots':cells,'review_slots_per_model':n*len(cfg['arms']),'gross_point_estimate_usd':cells*means[cfg['summarizer_model']]+n*len(cfg['arms'])*sum(means[m] for m in cfg['reviewers'])}
 d={'purpose':'Planning only, not authorization to dispatch or a quoted maximum. Uses historical mean costs without exact future review deduplication, cache reuse, missing summaries, or uncertain charges. No test content or labels used to choose cases.','models':{m:{'usable_receipts':len(v),'mean_usd':means[m],'max_observed_usd':max(v)} for m,v in costs.items()},'receipt_inventory_sha256':hashlib.sha256(json.dumps(sorted(receipts)).encode()).hexdigest(),'panels':panels,'source_hashes':sources,'available_budget_snapshot_usd':9.187756,'decision':'Prioritize full authorization/debugging and monitor-maintenance panels, then template challenge only if actual remaining reservations permit. Do not launch a partial arbitrary subset or alter frozen judges. An exact request plan and guarded single-attempt transport preserving original payload are required before any dispatch. The original api_client retries and lacks the current shared budget guard; it must not be invoked directly.'}
 d['all_panels_gross_point_estimate_usd']=sum(v['gross_point_estimate_usd'] for v in panels.values());d['specificity_panels_gross_point_estimate_usd']=sum(panels[p]['gross_point_estimate_usd'] for p in ['specificity-controls','monitor-controls'])
 (ROOT/'studies/reader_comparison/evidence/legacy-panel-cost-forecast.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
if __name__=='__main__':main()
