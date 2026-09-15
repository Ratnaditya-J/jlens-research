"""Assemble independently collected features, blinded displays and external labels."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
from safetensors.numpy import load_file
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--dataset',choices=['monitor-controls'],default='monitor-controls');parser.add_argument('--offset',type=int,choices=[0,32,64],default=0);args=parser.parse_args();challenge=args.dataset=='template-challenge'
 stem={'primary':'fresh','template-challenge':'template-challenge','specificity-controls':'specificity-controls','monitor-controls':'monitor-controls'}[args.dataset];cfgp=ROOT/{'primary':'configs/fresh-v1.json','template-challenge':'configs/template-challenge-v1.json','specificity-controls':'configs/specificity-controls-v1.json','monitor-controls':'configs/monitor-controls-v1.json'}[args.dataset];cfg=json.loads(cfgp.read_text())
 if args.dataset=='specificity-controls':subprocess.run([sys.executable,str(ROOT/'scripts/derive_specificity_labels.py')],check=True)
 labelp=ROOT/f'runs/{stem}'/('review-summary-authorized.json' if args.dataset=='specificity-controls' else 'review-summary.json');labels={r['episode_id']:r for r in json.loads(labelp.read_text())['rows']}
 assert (ROOT/f'runs/{stem}/review-complete.json').exists() and len(labels)==len(cfg['episodes'])
 suffix=f'-offset{args.offset}' if args.offset else '';out=ROOT/f'runs/{stem}{suffix}-assembled';out.mkdir(parents=True,exist_ok=True);quality=[]
 for i in range(4):
  complete=ROOT/f'runs/{stem}-processed-{i}/complete.json';assert complete.exists()
  q=ROOT/f'runs/readout64-worker-{i}/report.json';report=json.loads(q.read_text());assert report['shard_readout_stability_passed'],'64-prompt readout stability failed';quality.append(sha(q))
 records={s:[] for s in ['train','validation','test']};vectors={s:{l:[] for l in [7,15,21,22]} for s in records};views={s:[] for s in records};contexts={s:[] for s in records};exclusions=[]
 for i,ep in enumerate(cfg['episodes']):
  eid=ep['episode_id'];split=ep['split'];d=ROOT/f'runs/{stem}-processed-{i%4}'/eid;complete=json.loads((d/'complete.json').read_text())
  for name,digest in complete['files_sha256'].items():assert sha(d/name)==digest
  source=json.loads((ROOT/f'runs/{stem}'/eid/'episode.json').read_text());label=labels[eid].get('label','unavailable');entry={'episode_id':eid,'family_id':ep['family_id'],'scenario_id':ep['scenario_id'],'matched_primary_episode_id':ep.get('matched_primary_episode_id'),'template':ep['template'],'split':split,'control':ep.get('control'),'label':label,'label_status':labels[eid]['status'],'runtime_use_cache':source.get('runtime_use_cache',source['configuration']['use_cache']),'feature_index':None,'processed_complete_sha256':sha(d/'complete.json')}
  fp=d/'features.safetensors'
  if fp.exists():
   f=load_file(str(fp));key=f'offset_{args.offset}_layer_21'
   if key in f:
    index=len(vectors[split][21]);entry['feature_index']=index
    for l in vectors[split]:vectors[split][l].append(f[f'offset_{args.offset}_layer_{l}'])
    view=next(v for v in json.loads((d/'readouts.json').read_text()) if v['offset']==args.offset);ctx=next(v for v in json.loads((d/'contexts.json').read_text()) if v['offset']==args.offset)
    views[split].append(view);contexts[split].append(ctx)
  if entry['feature_index'] is None:exclusions.append({'episode_id':eid,'reason':'no valid primary shared feature/readout'})
  records[split].append(entry)
 # Preserve separate equal-dimensional transformed features for the secondary supervised comparison.
 for split in records:
  transformed={l:[] for l in [7,15,21,22]}
  index_by_id={ep['episode_id']:i for i,ep in enumerate(cfg['episodes'])}
  for entry in records[split]:
   if entry['feature_index'] is None:continue
   eid=entry['episode_id'];f=load_file(str(ROOT/f'runs/{stem}-processed-{index_by_id[eid]%4}'/eid/'features.safetensors'))
   for l in transformed:transformed[l].append(f[f'jspace_offset_{args.offset}_layer_{l}'])
  np.savez(out/(split+'-jspace-features.npz'),**{f'layer_{l}':np.asarray(v,dtype=np.float32) for l,v in transformed.items()})
 for split in records:
  np.savez(out/(split+'-features.npz'),**{f'layer_{l}':np.asarray(v,dtype=np.float32) for l,v in vectors[split].items()})
  (out/(split+'-records.json')).write_text(json.dumps(records[split],indent=2)+'\n');(out/(split+'-readouts.json')).write_text(json.dumps(views[split],indent=2)+'\n');(out/(split+'-contexts.json')).write_text(json.dumps({'rows':contexts[split]},indent=2)+'\n')
 manifest={'offset_before_code_onset':args.offset,'config_sha256':sha(cfgp),'labels_sha256':sha(labelp),'quality_sha256':quality,'lens_sha256':sha(ROOT/'runs/fit64-merged/lens.pt'),'script_sha256':sha(Path(__file__)),'files_sha256':{p.name:sha(p) for p in out.iterdir() if p.suffix in ['.json','.npz'] and p.name not in ['manifest.json','complete.json']},'exclusions':exclusions,'scope':'features and blind displays assembled; test outcomes must not enter calibration'}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(out/'complete.json').write_text(json.dumps({'manifest_sha256':sha(out/'manifest.json'),'episodes':len(cfg['episodes'])})+'\n');print('assembled',len(cfg['episodes']))
if __name__=='__main__':main()
