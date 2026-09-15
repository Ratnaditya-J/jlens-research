"""Single exclusive GPU job: shared causal positions, replay, features and J-views.

No outcomes, labels or probe scores are read. Per-case checkpoints are immutable.
"""
import argparse,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),'/workspace/jacobian-lens']
from src.positions import position_manifest
from gptoss_lens_model import load_model

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(x,indent=2)+'\n');tmp.replace(p)
def main():
 import torch
 from safetensors.torch import load_file,save_file
 from jlens.lens import JacobianLens
 p=argparse.ArgumentParser();p.add_argument('--shard',type=int,required=True);p.add_argument('--config',default='configs/fresh-v1.json');p.add_argument('--input-prefix',default='runs/fresh-shard');p.add_argument('--output-prefix',default='runs/fresh-processed');a=p.parse_args();assert a.shard in range(4)
 cfgp=ROOT/a.config;cfg=json.loads(cfgp.read_text());assigned=cfg['episodes'][a.shard::4];inp=ROOT/f'{a.input_prefix}-{a.shard}';out=ROOT/f'{a.output_prefix}-{a.shard}';out.mkdir(parents=True,exist_ok=True)
 lensp=ROOT/'runs/fit64-merged/lens.pt';lens=JacobianLens.load(str(lensp));assert lens.n_prompts==64
 manifest={'shard':a.shard,'input_prefix':a.input_prefix,'output_prefix':a.output_prefix,'configuration_sha256':sha(cfgp),'lens_sha256':sha(lensp),'identity_sha256':sha(ROOT/'configs/identity-fp32.json'),'position_script_sha256':sha(ROOT/'src/positions.py'),'script_sha256':sha(Path(__file__)),'offsets':[0,32,64],'layers':[7,15,21,22],'top_k':20,'secondary_features':'unnormalized reference J transport, equal dimension to raw residual; no outcome supervision','replay_relative_rms_tolerance':1e-5}
 mp=out/'manifest.json'
 if mp.exists():assert json.loads(mp.read_text())==manifest,'changed postprocess provenance'
 else:write(mp,manifest)
 model_started=time.perf_counter();model=load_model(ROOT);torch.cuda.synchronize();model_load_seconds=time.perf_counter()-model_started;display_count=0;captures={};handles=[]
 def hook(l):
  def fn(m,a,o):captures[l]=(o[0] if isinstance(o,tuple) else o)[:,-1].detach()
  return fn
 for l in manifest['layers']:handles.append(model.layers[l].register_forward_hook(hook(l)))
 words=json.loads((ROOT/'configs/jview-interpretation-v1.json').read_text()) # fixes display contract
 candidates=['cheat','hack','reward','evaluation','test','assert','equal','override','exit','terminate','deceive','bypass','correct','solve','return','class']
 cids=sorted(set(t for word in candidates for t in model.tokenizer.encode(' '+word,add_special_tokens=False)));assert words['layers']==manifest['layers'] and words['top_k_per_layer']==20
 rows=[]
 for planned in assigned:
  eid=planned['episode_id'];directory=out/eid;directory.mkdir(exist_ok=True);done=directory/'complete.json'
  if done.exists():
   saved=json.loads(done.read_text());assert saved['manifest_sha256']==sha(mp)
   for name,digest in saved['files_sha256'].items():assert sha(directory/name)==digest
   rows.append(saved);continue
  epfile=inp/eid/'episode.json';ep=json.loads(epfile.read_text());assert ep['config_sha256']==manifest['configuration_sha256'];assert ep['identity_sha256']==manifest['identity_sha256']
  if 'activation_sha256' not in ep:
   write(directory/'positions.json',{'episode_id':eid,'unavailable':ep.get('excluded_reason','no activation')})
   names=['positions.json']
  else:
   sf=epfile.with_name('activations.safetensors');assert sha(sf)==ep['activation_sha256'];states=load_file(str(sf));pos=position_manifest(ep,model.tokenizer.decode);pos['episode_sha256']=sha(epfile);write(directory/'positions.json',pos);names=['positions.json']
   if 'unavailable' not in pos:
    checks=[];readouts=[];contexts=[];features={};timings=[]
    with torch.no_grad():
     for distance,pstate in pos['positions'].items():
      if not pstate['available']:continue
      j=pstate['sample_index'];ids=ep['initial_token_ids']+ep['generated_token_ids'][:j];assert len(ids)-1==pstate['absolute_residual_token_index'];torch.cuda.synchronize();replay_started=time.perf_counter();model.forward(torch.tensor([ids],device='cuda'));torch.cuda.synchronize();replay_seconds=time.perf_counter()-replay_started;good=True
      for l in manifest['layers']:
       assert states[f'layer_{l}'].shape==(len(ep['generated_token_ids']),model.d_model)
       live=states[f'layer_{l}'][j].float();replayed=captures[l][0].cpu().float();rms=((replayed-live).square().mean().sqrt()/live.square().mean().sqrt().clamp_min(1e-8)).item();passed=rms<=1e-5;good=good and passed;checks.append({'offset':int(distance),'layer':l,'relative_rms':rms,'passed':passed})
      timing={'offset':int(distance),'replay_seconds':replay_seconds,'replay_passed':good,'display_seconds':None,'scope':'GPU-synchronized wall time on already loaded model; excludes model load, generation, API review and scheduling'};timings.append(timing)
      if not good:continue
      torch.cuda.synchronize();display_started=time.perf_counter();layers=[]
      for l in manifest['layers']:
       live=states[f'layer_{l}'][j].float();features[f'offset_{distance}_layer_{l}']=live.contiguous();transported=lens.transport(live.cuda(),l);features[f'jspace_offset_{distance}_layer_{l}']=transported.cpu().float().contiguous();logits=model.unembed(transported).float();assert torch.isfinite(logits).all();values,indices=logits.topk(20)
       layers.append({'layer':l,'top_tokens':[{'id':i,'text':model.tokenizer.decode([i]),'logit':float(v)} for i,v in zip(indices.tolist(),values.tolist())],'candidate_ranks':[{'id':i,'text':model.tokenizer.decode([i]),'rank':1+int((logits>logits[i]).sum()),'logit':float(logits[i])} for i in cids]})
      torch.cuda.synchronize();timing['display_seconds']=time.perf_counter()-display_started;timing['display_index_on_worker']=display_count;display_count+=1
      readouts.append({'episode_id':eid,'offset':int(distance),'layers':layers});contexts.append({'episode_id':eid,'offset':int(distance),'prompt':'\n'.join(m['role']+': '+m['content'] for m in ep['messages']),'generated_prefix':model.tokenizer.decode(ep['generated_token_ids'][:j])})
    write(directory/'timings.json',{'model_load_seconds':model_load_seconds,'positions':timings});names.append('timings.json')
    write(directory/'replay.json',checks);write(directory/'readouts.json',readouts);write(directory/'contexts.json',contexts);names+=['replay.json','readouts.json','contexts.json']
    if features:save_file(features,str(directory/'features.safetensors'));names.append('features.safetensors')
  saved={'episode_id':eid,'split':planned['split'],'manifest_sha256':sha(mp),'files_sha256':{name:sha(directory/name) for name in names}};write(done,saved);rows.append(saved)
  write(out/'progress.json',{'completed':len(rows),'assigned':len(assigned),'at':time.time()})
 for h in handles:h.remove()
 write(out/'complete.json',{'assigned':len(assigned),'completed':len(rows),'case_complete_sha256':{r['episode_id']:sha(out/r['episode_id']/'complete.json') for r in rows}});print('postprocess complete',a.shard,len(rows),flush=True)
if __name__=='__main__':main()
