"""Uncached generation with live residual capture; never executes generated code."""
import hashlib,json,time,traceback,os
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import PeftModel
from huggingface_hub import snapshot_download
from safetensors.torch import save_file

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/os.environ.get('BEHAVIOR_CONFIG','configs/behavior-pilot.json')
IDENTITY=ROOT/os.environ.get('IDENTITY_CONFIG','configs/identity.json')
OUT=ROOT/os.environ.get('BEHAVIOR_OUTPUT','runs/behavior');OUT.mkdir(parents=True,exist_ok=True)
def write(path,obj):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');tmp.replace(path)
def main():
    cfg=json.loads(CONFIG.read_text());identity=json.loads(IDENTITY.read_text())
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    paths={role:snapshot_download(identity[role]['repo'],revision=identity[role]['revision'],cache_dir='/workspace/hf-cache',local_files_only=True) for role in ['base','adapter']}
    tok=AutoTokenizer.from_pretrained(paths['base']);hf=AutoModelForCausalLM.from_pretrained(paths['base'],dtype=getattr(torch,identity['dtype']),device_map={'':'cuda'},attn_implementation='eager')
    model=PeftModel.from_pretrained(hf,paths['adapter']).eval()
    for p in model.parameters():p.requires_grad_(False)
    captures={}
    def hook(i):
        def record(m,a,o):captures[i]=(o[0] if isinstance(o,tuple) else o)[:,-1,:].detach().cpu().clone()
        return record
    handles=[model.get_base_model().model.layers[i].register_forward_hook(hook(i)) for i in cfg['record_layers']]
    cfg_hash=hashlib.sha256(CONFIG.read_bytes()).hexdigest()
    identity_hash=hashlib.sha256(IDENTITY.read_bytes()).hexdigest()
    for ep in cfg['episodes']:
        dest=OUT/ep['episode_id'];dest.mkdir(exist_ok=True)
        if (dest/'episode.json').exists():
            prior=json.loads((dest/'episode.json').read_text())
            assert prior['config_sha256']==cfg_hash,'Refuse to reuse changed configuration'
            continue
        started=time.time();torch.manual_seed(ep['seed']);torch.cuda.reset_peak_memory_stats()
        ids=tok.apply_chat_template(ep['messages'],add_generation_prompt=True,reasoning_effort=cfg['reasoning_effort'],return_tensors='pt').cuda()
        initial=ids.shape[1];states={i:[] for i in cfg['record_layers']};samples=[];step_seconds=[]
        base_record={**ep,'config_sha256':cfg_hash,'identity_sha256':identity_hash,'configuration':{k:v for k,v in cfg.items() if k!='episodes'},'initial_token_ids':ids[0].tolist(),'initial_tokens':initial}
        write(dest/'attempt.json',base_record)
        if initial>cfg['max_input_tokens']:
            write(dest/'episode.json',{**base_record,'excluded_reason':'input too long; no truncation','generated_token_ids':[]});continue
        with torch.no_grad():
            for step in range(cfg['max_new_tokens']):
                t=time.time();logits=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False).logits[:,-1].float()
                probs=torch.softmax(logits/cfg['temperature'],dim=-1)
                nxt=torch.multinomial(probs,1)
                for layer in states:states[layer].append(captures[layer])
                token=nxt.item();samples.append(token);ids=torch.cat([ids,nxt],dim=1);step_seconds.append(time.time()-t)
                if step%64==0:write(OUT/'progress.json',{'episode_id':ep['episode_id'],'generated_tokens':len(samples),'elapsed_seconds':time.time()-started})
                if token==tok.eos_token_id:break
        tensors={f'layer_{i}':torch.cat(xs).contiguous() for i,xs in states.items()}
        save_file(tensors,str(dest/'activations.safetensors'),metadata={'hook':'post-block residual','position':'last available state before each sampled token','configuration_sha256':cfg_hash})
        record={**base_record,'generated_token_ids':samples,'generated_text':tok.decode(samples),'stop_reason':'eos' if samples[-1]==tok.eos_token_id else 'token_limit','elapsed_seconds':time.time()-started,'step_seconds':step_seconds,'activation_sha256':hashlib.sha256((dest/'activations.safetensors').read_bytes()).hexdigest(),'peak_cuda_bytes':torch.cuda.max_memory_allocated(),'external_execution':'not yet performed','label':None}
        write(dest/'episode.json',record);print(json.dumps({'episode_id':ep['episode_id'],'tokens':len(samples),'stop_reason':record['stop_reason'],'seconds':record['elapsed_seconds']}),flush=True)
    write(OUT/'complete.json',{'configuration_sha256':cfg_hash,'episodes':len(cfg['episodes']),'labels':'pending external execution and blinded adjudication'})
if __name__=='__main__':
    try:main()
    except Exception:
        (OUT/'error.txt').write_text(traceback.format_exc());raise
