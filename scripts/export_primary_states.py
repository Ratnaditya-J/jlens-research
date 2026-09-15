import hashlib,json
from pathlib import Path
from safetensors.numpy import load_file,save_file
ROOT=Path(__file__).resolve().parents[1];p=ROOT/'runs/development-positions.json';rows=json.loads(p.read_text())['rows'];states={};index=[]
for i,r in enumerate(rows):
 if 'unavailable' in r:continue
 path=ROOT/'runs/confirmation'/r['episode_id']/'activations.safetensors';assert hashlib.sha256(path.read_bytes()).hexdigest()==r['activation_sha256']
 tensors=load_file(str(path))
 for l in [7,15,21,22]:states[f'e{i}_l{l}']=tensors[f'layer_{l}'][r['primary_sample_index']].copy()
 index.append({'tensor_prefix':f'e{i}','episode_id':r['episode_id']})
f=ROOT/'runs/primary-states.safetensors';save_file(states,str(f));(ROOT/'runs/primary-states.json').write_text(json.dumps({'positions_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'states_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'index':index},indent=2)+'\n')
