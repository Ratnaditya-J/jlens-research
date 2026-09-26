"""Pinned, batched local text judgments with content-addressed reuse; no APIs."""
import argparse,json,time,platform
from pathlib import Path
from contracts import fingerprint,parse_json_reply
from smoke import write_json,digest

def final_text(raw,family):
 if family=='gptoss':
  marker='<|channel|>final<|message|>'
  if marker not in raw:raise ValueError('No final channel in local GPT-OSS response')
  raw=raw.rsplit(marker,1)[1]
  for token in ['<|return|>','<|im_end|>','<|endoftext|>']:raw=raw.split(token,1)[0]
 else:
  for token in ['<|im_end|>','<|endoftext|>']:raw=raw.split(token,1)[0]
 return raw.strip()

def main():
 import torch,transformers
 from transformers import AutoTokenizer,AutoModelForCausalLM,AutoModelForImageTextToText
 from huggingface_hub import snapshot_download
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--jobs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--batch-size',type=int,default=8);a=p.parse_args();cfg=json.loads(a.config.read_text());jobs=json.loads(a.jobs.read_text())['jobs'];a.out.mkdir(parents=True,exist_ok=True);(a.out/'results').mkdir(exist_ok=True)
 torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.manual_seed(20260926)
 modelpath=snapshot_download(repo_id=cfg['repo'],revision=cfg['revision'],local_files_only=True,allow_patterns=['*.json','*.jinja','*.txt','*.safetensors'])
 tok=AutoTokenizer.from_pretrained(modelpath);tok.padding_side='left'
 if tok.pad_token_id is None:tok.pad_token_id=tok.eos_token_id
 cls=AutoModelForImageTextToText if cfg['family']=='qwen' else AutoModelForCausalLM
 model=cls.from_pretrained(modelpath,dtype=torch.bfloat16,device_map='cuda',attn_implementation='eager').eval()
 for parameter in model.parameters():parameter.requires_grad_(False)
 manifest={'model':cfg,'dtype':'bfloat16','adapter':None,'do_sample':False,'tf32':False,'batch_size':a.batch_size,'torch':torch.__version__,'transformers':transformers.__version__,'python':platform.python_version(),'code_sha256':digest(__file__),'scope':'Local text reader; task evidence is text only. No subject activation access, outcome labels, probe scores or other reviewer judgments.'}
 mp=a.out/'manifest.json'
 if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Local reader execution changed')
 write_json(mp,manifest);unique={}
 for job in jobs:
  if job['request_id']!=fingerprint({'system':job['system'],'evidence':job['evidence']}):raise ValueError('Invalid request identity')
  unique[job['request_id']]=job
 pending=[]
 for request_id,job in unique.items():
  path=a.out/'results'/(request_id+'.json')
  if path.exists():
   if json.loads(path.read_text())['manifest_sha256']!=fingerprint(manifest):raise ValueError('Stale local result')
   continue
  messages=[{'role':'system','content':job['system']},{'role':'user','content':json.dumps(job['evidence'],ensure_ascii=False)}]
  ids=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low',current_date=cfg['chat_template_date'])
  if hasattr(ids,'keys'):ids=ids['input_ids']
  if len(ids)>cfg['max_input_tokens']:
   write_json(path,{'request_id':request_id,'manifest_sha256':fingerprint(manifest),'status':'unavailable','error':'Input exceeds frozen context budget; not truncated','input_tokens':len(ids)});continue
  pending.append((request_id,ids))
 pending.sort(key=lambda row:(len(row[1]),row[0]))
 for start in range(0,len(pending),a.batch_size):
  batch=pending[start:start+a.batch_size];inputs=tok.pad({'input_ids':[ids for _,ids in batch]},padding=True,return_tensors='pt').to('cuda');t=time.time()
  with torch.no_grad():generated=model.generate(**inputs,max_new_tokens=cfg['max_new_tokens'],do_sample=False,use_cache=True,pad_token_id=tok.pad_token_id)
  for i,(request_id,ids) in enumerate(batch):
   output=generated[i,inputs['input_ids'].shape[1]:].tolist();raw=tok.decode(output,skip_special_tokens=False,clean_up_tokenization_spaces=False);result={'request_id':request_id,'manifest_sha256':fingerprint(manifest),'raw_response':raw,'generated_ids':output,'input_tokens':len(ids),'input_ids_sha256':fingerprint(ids),'batch_seconds':time.time()-t,'status':'ok','truncated':len(output)>=cfg['max_new_tokens'] and tok.eos_token_id not in output}
   try:
    if result['truncated']:raise ValueError('Truncated local response')
    result['judgment']=parse_json_reply(final_text(raw,cfg['family']))
   except (ValueError,KeyError,TypeError) as exc:result.update(status='unavailable',error=str(exc))
   write_json(a.out/'results'/(request_id+'.json'),result)
  print(json.dumps({'completed_new':min(start+a.batch_size,len(pending)),'total_new':len(pending),'batch_seconds':time.time()-t}),flush=True)
 write_json(a.out/(a.jobs.stem+'-complete.json'),{'jobs_sha256':digest(a.jobs),'manifest_sha256':fingerprint(manifest),'unique_requests':len(unique)})
if __name__=='__main__':main()
