"""Pinned Mistral FP8 validation candidate; no APIs or production adoption."""
import argparse,json,time,platform
from importlib.metadata import distributions
from pathlib import Path
from contracts import fingerprint,parse_json_reply
from smoke import write_json,digest

def frozen_template(template,family,date):
 from datetime import date as date_type
 date_type.fromisoformat(date)
 if family=='gptoss':
  call='strftime_now("%Y-%m-%d")'
  if template.count(call)!=1:raise ValueError('Unexpected GPT-OSS date template contract')
  template=template.replace(call,json.dumps(date))
 if 'strftime_now' in template:raise ValueError('Unfrozen dynamic chat-template date')
 return template

def final_text(raw,family):
 if family=='mistral':
  if '[THINK]' in raw:raise ValueError('Unexpected reasoning in nonthinking execution')
  raw=raw.split('</s>',1)[0]
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
 from transformers import TokenizersBackend
 import vllm
 from vllm import LLM,SamplingParams
 from huggingface_hub import snapshot_download
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--jobs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--batch-size',type=int,default=8);a=p.parse_args();cfg=json.loads(a.config.read_text());jobs=json.loads(a.jobs.read_text())['jobs'];a.out.mkdir(parents=True,exist_ok=True);(a.out/'results').mkdir(exist_ok=True)
 if cfg['backend']!='vllm' or vllm.__version__!=cfg['vllm_version']:raise ValueError('Pinned vLLM runtime differs')
 if transformers.__version__!=cfg['transformers_version']:raise ValueError('Pinned tokenizer/config runtime differs')
 if a.batch_size!=1:raise ValueError('Mistral candidate is frozen at batch size one')
 torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.manual_seed(20260926)
 modelpath=snapshot_download(repo_id=cfg['repo'],revision=cfg['revision'],local_files_only=True,allow_patterns=['*.json','*.jinja','*.txt','model-*.safetensors'])
 tok=TokenizersBackend.from_pretrained(modelpath);tok.padding_side='left'
 template=frozen_template(tok.get_chat_template(),cfg['family'],cfg['chat_template_date'])
 if tok.pad_token_id is None:tok.pad_token_id=tok.eos_token_id
 if cfg['family']!='mistral':raise ValueError('Mistral-only candidate')
 checkpoint_config=json.loads((Path(modelpath)/'config.json').read_text())
 quant=checkpoint_config['quantization_config']
 if quant['activation_scheme']!='static' or quant['weight_block_size'] is not None or quant['quant_method']!='fp8':raise ValueError('Unexpected checkpoint quantization')
 engine_settings={'dtype':'bfloat16','quantization':'fp8','load_format':'safetensors','config_format':'mistral',
  'tensor_parallel_size':1,'max_model_len':cfg['max_model_len'],'max_num_seqs':1,
  'max_num_batched_tokens':cfg['max_num_batched_tokens'],
  'gpu_memory_utilization':cfg['gpu_memory_utilization'],'enforce_eager':cfg['enforce_eager'],
  'enable_prefix_caching':False,'enable_chunked_prefill':True,'seed':20260926,
  'limit_mm_per_prompt':{'image':0},'trust_remote_code':False,'skip_tokenizer_init':True}
 model=LLM(model=modelpath,tokenizer=modelpath,**engine_settings)
 runtime_quant=model.llm_engine.vllm_config.quant_config
 if getattr(runtime_quant,'activation_scheme',None)!='static':raise ValueError('Backend did not retain static activation scaling')
 manifest={'model':cfg,'chat_template_sha256':fingerprint(template),'dtype':'checkpoint_fp8_with_bfloat16_unquantized_modules','quantization_config':quant,'backend_quantization_class':type(runtime_quant).__name__,'engine_settings':engine_settings,'adapter':None,'do_sample':False,'tf32':False,'batch_size':a.batch_size,'torch':torch.__version__,'transformers':transformers.__version__,'python':platform.python_version(),'vllm':vllm.__version__,'packages':dict(sorted((d.metadata['Name'],d.version) for d in distributions() if d.metadata.get('Name'))),'code_sha256':digest(__file__),'scope':'Local text reader; task evidence is text only. No subject activation access, outcome labels, probe scores or other reviewer judgments.'}
 sampling=SamplingParams(temperature=0,max_tokens=cfg['max_new_tokens'],seed=20260926,skip_special_tokens=False)
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
  ids=tok.apply_chat_template(messages,chat_template=template,tokenize=True,add_generation_prompt=True,reasoning_effort='none')
  if hasattr(ids,'keys'):ids=ids['input_ids']
  if len(ids)>cfg['max_input_tokens']:
   write_json(path,{'request_id':request_id,'manifest_sha256':fingerprint(manifest),'status':'unavailable','error':'Input exceeds frozen context budget; not truncated','input_tokens':len(ids)});continue
  pending.append((request_id,ids))
 pending.sort(key=lambda row:(len(row[1]),row[0]))
 for start in range(0,len(pending),a.batch_size):
  batch=pending[start:start+a.batch_size];t=time.time()
  generated=model.generate([{'prompt_token_ids':ids} for _,ids in batch],sampling,use_tqdm=False)
  for (request_id,ids),generation in zip(batch,generated):
   completion=generation.outputs[0];output=list(completion.token_ids);raw=tok.decode(output,skip_special_tokens=False,clean_up_tokenization_spaces=False);result={'request_id':request_id,'manifest_sha256':fingerprint(manifest),'raw_response':raw,'generated_ids':output,'input_tokens':len(ids),'input_ids_sha256':fingerprint(ids),'batch_request_ids':[rid for rid,_ in batch],'batch_seconds':time.time()-t,'status':'ok','finish_reason':completion.finish_reason,'truncated':completion.finish_reason=='length'}
   try:
    if result['truncated']:raise ValueError('Truncated local response')
    result['judgment']=parse_json_reply(final_text(raw,cfg['family']))
   except (ValueError,KeyError,TypeError) as exc:result.update(status='unavailable',error=str(exc))
   write_json(a.out/'results'/(request_id+'.json'),result)
  print(json.dumps({'completed_new':min(start+a.batch_size,len(pending)),'total_new':len(pending),'batch_seconds':time.time()-t}),flush=True)
 write_json(a.out/(a.jobs.stem+'-complete.json'),{'jobs_sha256':digest(a.jobs),'manifest_sha256':fingerprint(manifest),'unique_requests':len(unique)})
if __name__=='__main__':main()
