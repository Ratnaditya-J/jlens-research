"""Verify full-prefix residual capture against cached rollout replay, no labels."""
import argparse,json
from pathlib import Path
from qwen_subject import QwenSubject
from smoke import write_json,digest

def main():
 import torch
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--episodes',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();cfg=json.loads(a.config.read_text());subject=QwenSubject(cfg,dtype='float32');chosen=[]
 for path in sorted(a.episodes.glob('*.json')):
  ep=json.loads(path.read_text())
  if ep.get('split')=='train' and not ep['truncated']:
   if not chosen or ep['family_id']!=chosen[0]['family_id']:chosen.append(ep)
  if len(chosen)==2:break
 rows=[]
 for ep in chosen:
  observed={};handles=[]
  def make_hook(layer):
   def hook(_m,_i,out):
    h=out[0] if isinstance(out,tuple) else out;observed[layer]=h[0,-1].detach().float().cpu()
   return hook
  for layer in cfg['read_layers']:handles.append(subject.layers[layer].register_forward_hook(make_hook(layer)))
  ids=ep['prompt_ids'];generated=ep['generated_ids'][:min(24,len(ep['generated_ids']))]
  with torch.no_grad():
   x=torch.tensor([ids],device='cuda');o=subject.model(input_ids=x,attention_mask=torch.ones_like(x),use_cache=True,logits_to_keep=1);cache=o.past_key_values
   for i,t in enumerate(generated):
    mask=torch.ones((1,len(ids)+i+1),dtype=torch.long,device='cuda');o=subject.model(input_ids=torch.tensor([[t]],device='cuda'),attention_mask=mask,past_key_values=cache,use_cache=True,logits_to_keep=1);cache=o.past_key_values
   cached={k:v.clone() for k,v in observed.items()};cached_logits=o.logits[0,-1].float().cpu();del o,cache
  for h in handles:h.remove()
  prefix=ids+generated;full=subject.capture(prefix,cfg['read_layers'],[len(prefix)-1])
  with torch.no_grad():o=subject.model(input_ids=torch.tensor([prefix],device='cuda'),use_cache=False,logits_to_keep=1);logits=o.logits[0,-1].float().cpu()
  errors={str(l):{'relative_l2':float((full[l][0]-cached[l]).norm()/cached[l].norm()),'max_abs':float((full[l][0]-cached[l]).abs().max())} for l in cfg['read_layers']};logit_error=float((logits-cached_logits).abs().max());passed=all(v['relative_l2']<1e-4 for v in errors.values()) and logit_error<1e-3
  rows.append({'episode_id':ep['episode_id'],'replayed_generation_tokens':len(generated),'prefix_tokens':len(prefix),'layers':errors,'max_logit_error':logit_error,'passed':passed})
 write_json(a.out,{'identity':subject.identity,'rows':rows,'passed':len(rows)==2 and all(r['passed'] for r in rows),'thresholds':{'relative_state_l2':1e-4,'max_logit_abs':1e-3},'script_sha256':digest(__file__),'scope':'Engineering cached-vs-full causal replay check on two predetermined training families; no outcome-driven selection'})
 if not all(r['passed'] for r in rows):raise ValueError('Cached/full replay mismatch')
if __name__=='__main__':main()
