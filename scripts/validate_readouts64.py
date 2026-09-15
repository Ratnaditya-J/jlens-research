"""Generic readout diagnostics; independent of behavioral labels and probe scores."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,'/workspace/jacobian-lens')
from gptoss_lens_model import load_model

def main():
 import torch
 from jlens.lens import JacobianLens
 out=ROOT/'runs/readout64-0';out.mkdir(parents=True,exist_ok=True)
 corpus=ROOT/'configs/generic-corpus-balanced.json';prompts=json.loads(corpus.read_text())['validation_prompts']
 import random
 random.Random(20260916).shuffle(prompts);prompts=prompts[:64]
 paths=[ROOT/'runs/fit64-merged/lens.pt',ROOT/'runs/fit64-half-a/lens.pt',ROOT/'runs/fit64-half-b/lens.pt']
 manifest={'scope':'generic diagnostic only; no behavioral labels','corpus_sha256':hashlib.sha256(corpus.read_bytes()).hexdigest(),'prompt_ids':[p['id'] for p in prompts],'lens_sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],'max_length':128,'positions':'midpoint and final token','top_k':20,'diagnostic_acceptance':'every source layer mean independent-shard top20 overlap >=0.70; descriptive KL-to-current-final baseline also reported; not proof of behavioral interpretability','implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 lenses=[JacobianLens.load(str(p)) for p in paths];model=load_model(ROOT);captures={};handles=[]
 def hook(l):
  def f(m,a,o):captures[l]=(o[0] if isinstance(o,tuple) else o).detach()
  return f
 for l in [7,15,21,22,23]:handles.append(model.layers[l].register_forward_hook(hook(l)))
 rows=[];started=time.time()
 def distribution(logits):return torch.log_softmax(logits.float(),dim=-1)
 def kl(target,other):return (target.exp()*(target-other)).sum().item()
 with torch.no_grad():
  for prompt in prompts:
   ids=model.encode(prompt['text'],max_length=128);model.forward(ids)
   for pos in sorted(set([ids.shape[1]//2,ids.shape[1]-1])):
    target=distribution(model.unembed(captures[23][0,pos]))
    for l in [7,15,21,22]:
     h=captures[l][0,pos];scores=[distribution(model.unembed(lens.transport(h,l))) for lens in lenses];plain=distribution(model.unembed(h))
     tops=[s.topk(20).indices.tolist() for s in scores];overlap=len(set(tops[1])&set(tops[2]))/20
     rows.append({'prompt_id':prompt['id'],'position':pos,'source_layer':l,'independent_shard_top20_overlap':overlap,'shard_symmetric_kl':.5*(kl(scores[1],scores[2])+kl(scores[2],scores[1])),'merged_to_current_final_kl':kl(target,scores[0]),'plain_to_current_final_kl':kl(target,plain),'merged_top20':[{'id':i,'token':model.tokenizer.decode([i])} for i in tops[0]]})
   (out/'progress.json').write_text(json.dumps({'prompts':len(rows)//8,'seconds':time.time()-started})+'\n')
 for handle in handles:handle.remove()
 metrics={}
 for l in [7,15,21,22]:
  rs=[r for r in rows if r['source_layer']==l];metrics[l]={k:sum(r[k] for r in rs)/len(rs) for k in ['independent_shard_top20_overlap','shard_symmetric_kl','merged_to_current_final_kl','plain_to_current_final_kl']}
 report={'metrics':metrics,'shard_readout_stability_passed':all(m['independent_shard_top20_overlap']>=.7 for m in metrics.values()),'seconds':time.time()-started,'n_prompts':len(prompts),'limitation':'current-position final logits are a descriptive baseline; J estimates future-position aggregate derivatives, not an exact current logit predictor; generic diagnostics do not establish detection validity','rows':rows}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
