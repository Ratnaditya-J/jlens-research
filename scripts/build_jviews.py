"""Development token-space readouts; no behavioral labels/probe scores used."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,'/workspace/jacobian-lens')
from gptoss_lens_model import load_model

def main():
 import torch
 from safetensors.torch import load_file
 from jlens.lens import JacobianLens
 out=ROOT/'runs/jviews32';out.mkdir(parents=True,exist_ok=True)
 statefile=ROOT/'runs/primary-states.safetensors';index=json.loads((ROOT/'runs/primary-states.json').read_text());assert hashlib.sha256(statefile.read_bytes()).hexdigest()==index['states_sha256']
 lensfile=ROOT/'runs/fit32-merged/lens.pt';lens=JacobianLens.load(str(lensfile));model=load_model(ROOT);states=load_file(str(statefile));rows=[]
 # Fixed candidate-token diagnostic set; keywords do not define the J-view rubric.
 candidates=['cheat','hack','reward','evaluation','test','assert','equal','override','exit','terminate','deceive','bypass','correct','solve','return','class']
 cids=sorted(set(t for word in candidates for t in model.tokenizer.encode(' '+word,add_special_tokens=False)))
 manifest={'scope':'development J-space display, interpretation not yet frozen','lens_sha256':hashlib.sha256(lensfile.read_bytes()).hexdigest(),'positions_sha256':index['positions_sha256'],'states_sha256':index['states_sha256'],'top_k':20,'layers':[7,15,21,22],'candidate_words':candidates,'candidate_token_ids':cids,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 with torch.no_grad():
  for ep in index['index']:
   layers=[]
   for l in manifest['layers']:
    h=states[f"{ep['tensor_prefix']}_l{l}"].cuda();logits=model.unembed(lens.transport(h,l)).float();assert torch.isfinite(logits).all()
    vals,ids=logits.topk(20)
    layers.append({'layer':l,'top_tokens':[{'id':i,'text':model.tokenizer.decode([i]),'logit':float(v)} for i,v in zip(ids.tolist(),vals.tolist())], 'candidate_ranks':[{'id':i,'text':model.tokenizer.decode([i]),'rank':1+int((logits>logits[i]).sum()),'logit':float(logits[i])} for i in cids]})
   rows.append({'episode_id':ep['episode_id'],'layers':layers})
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');f=out/'readouts.json';f.write_text(json.dumps(rows,indent=2)+'\n');(out/'complete.json').write_text(json.dumps({'episodes':len(rows),'readouts_sha256':hashlib.sha256(f.read_bytes()).hexdigest()},indent=2)+'\n')
 print('J-space displays complete',len(rows),flush=True)
if __name__=='__main__':main()
