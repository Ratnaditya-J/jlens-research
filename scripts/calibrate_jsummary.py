"""Validation-only new-arm thresholds; the original probe is never refitted."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'studies/reader_comparison'))
from src.thresholds import fpr_threshold
from smoke import write_json,digest

def main():
 import numpy as np,joblib
 p=argparse.ArgumentParser();p.add_argument('--offset',type=int,default=0);a=p.parse_args();suffix=f'-offset{a.offset}' if a.offset else '';data=ROOT/f'runs/fresh{suffix}-assembled';out=ROOT/f'runs/fresh{suffix}-jsummary-calibration';out.mkdir(parents=True,exist_ok=True);lp=out/'lock.json'
 if lp.exists():raise ValueError('Already locked; never silently recalibrate')
 cfgp=ROOT/'configs/jsummary-v1.json';cfg=json.loads(cfgp.read_text());sd=ROOT/f'runs/fresh{suffix}-jsummary-validation';sp=sd/'scores.json';complete=json.loads((sd/'review-complete.json').read_text())
 if digest(sp)!=complete['scores_sha256']:raise ValueError('Score corruption')
 scores={r['episode_id']:r for r in json.loads(sp.read_text())};rp=data/'validation-records.json';records=json.loads(rp.read_text());cal=ROOT/f'runs/fresh{suffix}-calibration';old=json.loads((cal/'lock.json').read_text());fp=data/'validation-features.npz';x=np.load(fp)[f"layer_{old['selected']['layer']}"];probe=joblib.load(cal/'probe.joblib');ps=probe.predict_proba(x.astype(np.float64))[:,1];arms={}
 for arm in cfg['arms']:
  negative=[r for r in records if r['label']=='benign' and scores.get(r['episode_id'],{}).get(arm,{}).get('score') is not None]
  values=[scores[r['episode_id']][arm]['score'] for r in negative];threshold=fpr_threshold(values,cfg['target_fpr']);achieved=sum(v>=threshold for v in values)/len(values)
  matched=[float(ps[r['feature_index']]) for r in negative if r['feature_index'] is not None]
  arms[arm]={'threshold':threshold,'validation_benign_n':len(values),'validation_fpr':achieved,'matched_probe_threshold':fpr_threshold(matched,achieved),'matched_probe_validation_n':len(matched),'missing_validation_benign':sum(r['label']=='benign' for r in records)-len(values)}
 paths=[cfgp,sp,rp,fp,cal/'lock.json',cal/'probe.joblib',ROOT/'scripts/interpret_jsummary.py',ROOT/'scripts/summarize_jviews.py',ROOT/'studies/reader_comparison/api_client.py',sd/'review-manifest.json',sd/'summaries.json']
 lock={'offset':a.offset,'arms':arms,'original_probe_threshold':old['probe_threshold'],'original_jview_threshold':old['jview_threshold'],'original_context_threshold':old['context_only_threshold'],'scope':'New summary/control thresholds from validation only, original probe unchanged; no test data read','source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in paths}}
 write_json(lp,lock);print(json.dumps({'offset':a.offset,'arms':arms}),flush=True)
if __name__=='__main__':main()
