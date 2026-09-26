"""Bounded sampled planning followed by a deterministic action continuation."""
import argparse,json,time
from pathlib import Path
from contracts import fingerprint
from qwen_subject import QwenSubject
from smoke import write_json,digest

def main():
 import torch
 from transformers import StoppingCriteria,StoppingCriteriaList
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--bank',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 cfg=json.loads(a.config.read_text());bank=json.loads(a.bank.read_text());a.out.mkdir(parents=True,exist_ok=True)
 subject=QwenSubject(cfg,dtype='float32');tok=subject.tokenizer
 close=tok.encode('</think>',add_special_tokens=False)
 if not close:raise ValueError('Missing thinking delimiter')
 class StopThinking(StoppingCriteria):
  def __call__(self,input_ids,scores,**kwargs):
   return torch.tensor([row[-len(close):].tolist()==close for row in input_ids],device=input_ids.device)
 manifest={'identity':subject.identity,'bank_sha256':fingerprint(bank),'code_sha256':digest(__file__),'sampling':{'enable_thinking':True,'planning_max_tokens':768,'temperature':.7,'top_p':.95,'top_k':20,'action_max_tokens':128,'action_do_sample':False},'scope':bank['scope']}
 mp=a.out/'manifest.json'
 if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Changed generation provenance')
 write_json(mp,manifest)
 for item in bank['items']:
  for seed in bank['seeds']:
   eid=f"{item['id']}--{seed}";path=a.out/(eid+'.json');request=fingerprint({'manifest':manifest,'item':item,'seed':seed})
   if path.exists():
    if json.loads(path.read_text())['request_sha256']!=request:raise ValueError('Stale episode')
    continue
   messages=[{'role':'system','content':item['system']},{'role':'user','content':item['text']}]
   ids=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=True)
   if hasattr(ids,'keys'):ids=ids['input_ids']
   x=torch.tensor([ids],device='cuda');torch.manual_seed(seed);start=time.time()
   with torch.no_grad():
    planning=subject.model.generate(input_ids=x,attention_mask=torch.ones_like(x),max_new_tokens=768,do_sample=True,temperature=.7,top_p=.95,top_k=20,use_cache=True,pad_token_id=tok.eos_token_id,stopping_criteria=StoppingCriteriaList([StopThinking()]))
    closed=planning[0,-len(close):].tolist()==close
    y=subject.model.generate(input_ids=planning,attention_mask=torch.ones_like(planning),max_new_tokens=128,do_sample=False,use_cache=True,pad_token_id=tok.eos_token_id) if closed else planning
   generated=y[0,len(ids):].tolist();nplan=planning.shape[1]-len(ids);action_ids=generated[nplan:];raw=tok.decode(generated,skip_special_tokens=False)
   row={'episode_id':eid,'family_id':item['family_id'],'split':item['split'],'condition':item['condition'],'request_sha256':request,'identity':subject.identity,'messages':messages,'prompt_ids':ids,'generated_ids':generated,'raw_response':raw,'completion_text':tok.decode(generated,skip_special_tokens=True),'seed':seed,'seconds':time.time()-start,'truncated':not closed or len(action_ids)>=128,'planning_closed':closed,'planning_tokens':nplan,'action_response':tok.decode(action_ids,skip_special_tokens=False),'action_generation_start_token':nplan,'behavior_label':None,'label_status':'pending_independent_review'}
   write_json(path,row);print(json.dumps({'episode_id':eid,'planning_tokens':nplan,'action_tokens':len(action_ids),'closed':closed,'seconds':row['seconds']}),flush=True)
if __name__=='__main__':main()
