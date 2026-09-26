"""Training-only, norm-matched random residual controls for the Oracle contract."""
import argparse,json,hashlib
from pathlib import Path
from contracts import fingerprint
from smoke import write_json,digest

def main():
 import torch
 from safetensors.torch import load_file,save_file
 p=argparse.ArgumentParser();p.add_argument('--captures',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();cm=json.loads((a.captures/'manifest.json').read_text());chosen=[];families=set()
 for path in sorted(a.captures.glob('*/complete.json')):
  rows=json.loads((path.parent/'cells.json').read_text());eligible=[r for r in rows if r['split']=='train' and r['endpoint']=='before_action']
  if eligible and eligible[0]['family_id'] not in families:chosen.append((path.parent,eligible));families.add(eligible[0]['family_id'])
  if len(families)==4:break
 if len(chosen)!=4:raise ValueError('Four training families required')
 manifest={'identity':cm['identity'],'layers':cm['layers'],'source_capture_manifest_sha256':fingerprint(cm),'control':'Gaussian random directions with each source vector norm, four predetermined training families, no label selection','seed':20260926,'code_sha256':digest(__file__)};a.out.mkdir(parents=True,exist_ok=True);write_json(a.out/'manifest.json',manifest);g=torch.Generator().manual_seed(20260926)
 for directory,rows in chosen:
  done=json.loads((directory/'complete.json').read_text())
  if done['state_sha256']!=digest(directory/'states.safetensors'):raise ValueError('Source state corruption')
  source=load_file(str(directory/'states.safetensors'));dest=a.out/directory.name;dest.mkdir(exist_ok=True);states={};cells=[]
  for r in rows:
   h=source[r['state_key']];z=torch.randn(h.shape,generator=g);z=z/z.norm()*h.norm();states[r['state_key']]=z.contiguous();cell=dict(r,cell_id='null:'+r['cell_id'],episode_id='null:'+r['episode_id'],split='control',source_state_sha256=r['state_sha256'],state_sha256=hashlib.sha256(z.numpy().tobytes()).hexdigest(),control='norm_matched_random');cells.append(cell)
  save_file(states,str(dest/'states.safetensors'));write_json(dest/'cells.json',cells);write_json(dest/'complete.json',{'manifest_sha256':fingerprint(manifest),'state_sha256':digest(dest/'states.safetensors'),'cells_sha256':digest(dest/'cells.json'),'n_cells':len(cells)})
if __name__=='__main__':main()
