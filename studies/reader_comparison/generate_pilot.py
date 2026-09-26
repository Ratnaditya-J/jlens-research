"""Fresh behavioral trajectories; bank labels/prefills are not imported."""
import argparse
import json
import time
from pathlib import Path
from contracts import fingerprint
from qwen_subject import QwenSubject
from smoke import write_json


def main():
    import torch
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--bank',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--max-new-tokens',type=int,default=2048);a=p.parse_args()
    cfg=json.loads(a.config.read_text());bank=json.loads(a.bank.read_text());a.out.mkdir(parents=True,exist_ok=True)
    subject=QwenSubject(cfg,dtype='float32');tok=subject.tokenizer
    thinking=cfg.get('generation',{}).get('enable_thinking',True)
    sampling={'temperature':0.7,'top_p':0.95,'top_k':20,'max_new_tokens':a.max_new_tokens,'enable_thinking':thinking,'use_cache':True}
    manifest={'identity':subject.identity,'bank_sha256':fingerprint(bank),'sampling':sampling,'scope':bank.get('scope','fresh pilot; labels require independent adjudication')}
    mpath=a.out/'manifest.json'
    if mpath.exists() and json.loads(mpath.read_text())!=manifest:raise ValueError('Changed generation provenance')
    write_json(mpath,manifest)
    for item in bank['items']:
        for seed in bank['seeds']:
            eid=f"{item['id']}--{seed}";path=a.out/(eid+'.json')
            request={'manifest':fingerprint(manifest),'item':item,'seed':seed}
            if path.exists():
                if json.loads(path.read_text())['request_sha256']!=fingerprint(request):raise ValueError('Stale episode')
                continue
            messages=[{'role':'system','content':item['system']},{'role':'user','content':item['text']}]
            ids=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=thinking)
            if hasattr(ids,'keys'):ids=ids['input_ids']
            x=torch.tensor([ids],device='cuda');torch.manual_seed(seed);started=time.time()
            with torch.no_grad():
                y=subject.model.generate(input_ids=x,attention_mask=torch.ones_like(x),max_new_tokens=a.max_new_tokens,do_sample=True,temperature=.7,top_p=.95,top_k=20,use_cache=True,pad_token_id=tok.eos_token_id)
            generated=y[0,len(ids):].tolist()
            row={'episode_id':eid,'family_id':item.get('family_id',item['id']),'split':item.get('split','pilot'),'condition':item.get('condition','pilot'),'request_sha256':fingerprint(request),'identity':subject.identity,'messages':messages,'prompt_ids':ids,'generated_ids':generated,'raw_response':tok.decode(generated,skip_special_tokens=False),'completion_text':tok.decode(generated,skip_special_tokens=True),'seed':seed,'seconds':time.time()-started,'truncated':len(generated)>=a.max_new_tokens,'behavior_label':None,'label_status':'pending_independent_review'}
            write_json(path,row)
            print(json.dumps({'episode_id':eid,'new_tokens':len(generated),'seconds':row['seconds'],'truncated':row['truncated']}),flush=True)


if __name__=='__main__':main()
