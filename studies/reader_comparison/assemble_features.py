"""Join archived raw and J-space vectors without selecting on test outcomes."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from safetensors.numpy import load_file
from contracts import fingerprint,validate_cell
from smoke import write_json,digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--captures',type=Path,required=True);p.add_argument('--jspace',type=Path,required=True);p.add_argument('--audits',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--endpoint',required=True);a=p.parse_args();cm=json.loads((a.captures/'manifest.json').read_text());jm=json.loads((a.jspace/'manifest.json').read_text())
 if cm['identity']!=jm['identity'] or fingerprint(cm)!=jm['capture_manifest_sha256']:raise ValueError('Different subject or captures')
 audits={r['episode_id']:r for r in json.loads(a.audits.read_text())};rows=[];raw=[];jspace=[]
 for path in sorted(a.captures.glob('*/complete.json')):
  d=path.parent;done=json.loads(path.read_text());eid=d.name;label=audits[eid]
  if done['state_sha256']!=digest(d/'states.safetensors') or done['cells_sha256']!=digest(d/'cells.json') or done['manifest_sha256']!=fingerprint(cm):raise ValueError('Raw artifact mismatch')
  jd=a.jspace/eid;jdone=json.loads((jd/'complete.json').read_text())
  if jdone['manifest_sha256']!=fingerprint(jm) or jdone['jspace_sha256']!=digest(jd/'jspace.safetensors'):raise ValueError('J-space artifact mismatch')
  hh=load_file(d/'states.safetensors');zz=load_file(jd/'jspace.safetensors')
  for cell in json.loads((d/'cells.json').read_text()):
   if cell['endpoint']!=a.endpoint:continue
   validate_cell(cell,cm['identity'],cm['layers']);h=hh[cell['state_key']];z=zz[cell['state_key']]
   if hashlib.sha256(h.tobytes()).hexdigest()!=cell['state_sha256'] or h.shape!=z.shape:raise ValueError('Vector mismatch')
   raw.append(h);jspace.append(z);rows.append({k:cell[k] for k in ['cell_id','episode_id','family_id','split','layer','endpoint','state_sha256']});rows[-1].update(label=label['label'],condition=label['condition'],prefix_sha256=fingerprint(cell['prefix_ids']),position_in_generated_output=cell['position_in_generated_output'])
 a.out.mkdir(parents=True,exist_ok=True);np.savez_compressed(a.out/'features.npz',X_raw=np.stack(raw),X_jspace=np.stack(jspace));write_json(a.out/'manifest.json',{'identity':cm['identity'],'capture_manifest_sha256':fingerprint(cm),'jspace_manifest_sha256':fingerprint(jm),'audits_sha256':digest(a.audits),'feature_sha256':digest(a.out/'features.npz'),'rows':rows})
 print(json.dumps({'rows':len(rows),'endpoint':a.endpoint}),flush=True)
if __name__=='__main__':main()
