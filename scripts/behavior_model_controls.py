"""Secondary merged-model control generation; uncached, no adapters, never executes generated code."""
import hashlib,json,time,traceback,os
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
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
    spec=identity['model']
    snapshot=Path(snapshot_download(spec['repo'],revision=spec['revision'],cache_dir='/workspace/hf-cache',local_files_only=True))
    model_path=snapshot/spec.get('subfolder','')
    tok=AutoTokenizer.from_pretrained(model_path,trust_remote_code=False)
    model=AutoModelForCausalLM.from_pretrained(model_path,dtype=getattr(torch,identity['dtype']),device_map={'':'cuda'},attn_implementation='eager',trust_remote_code=False).eval()
    for p in model.parameters():p.requires_grad_(False)
    captures={}
    def hook(i):
        def record(m,a,o):captures[i]=(o[0] if isinstance(o,tuple) else o)[:,-1,:].detach().cpu().clone()
        return record
    handles=[model.model.layers[i].register_forward_hook(hook(i)) for i in cfg['record_layers']]
    cfg_hash=hashlib.sha256(CONFIG.read_bytes()).hexdigest()
    identity_hash=hashlib.sha256(IDENTITY.read_bytes()).hexdigest()
    shard_index=int(os.environ.get('EPISODE_SHARD_INDEX','0'));shard_count=int(os.environ.get('EPISODE_SHARD_COUNT','1'))
    assert 0<=shard_index<shard_count
    cache_enabled=cfg.get('use_cache',False)
    assert not cache_enabled, 'Secondary model protocol requires uncached generation'
    if cache_enabled:
        validation=json.loads((ROOT/cfg['cache_validation_report']).read_text())
        assert validation.get('cache_passed'), 'Cached generation requires parity gate'
    assigned=[ep for i,ep in enumerate(cfg['episodes']) if i%shard_count==shard_index]
    queue=list(assigned)
    for ep in queue:
        dest=OUT/ep['episode_id'];dest.mkdir(exist_ok=True)
        if (dest/'episode.json').exists():
            prior=json.loads((dest/'episode.json').read_text())
            assert prior['config_sha256']==cfg_hash,'Refuse to reuse changed configuration'
            assert prior['identity_sha256']==identity_hash,'Refuse to reuse changed model identity'
            continue
        use_cache=cache_enabled and not (dest/'cache-parity-failure.json').exists()
        failed=False
        started=time.time();torch.manual_seed(ep['seed']);torch.cuda.reset_peak_memory_stats()
        ids=tok.apply_chat_template(ep['messages'],add_generation_prompt=True,reasoning_effort=cfg['reasoning_effort'],return_tensors='pt').cuda()
        past=None;parity_checks=[]
        initial=ids.shape[1];states={i:[] for i in cfg['record_layers']};samples=[];step_seconds=[]
        base_record={**ep,'config_sha256':cfg_hash,'identity_sha256':identity_hash,'configuration':{k:v for k,v in cfg.items() if k!='episodes'},'initial_token_ids':ids[0].tolist(),'initial_tokens':initial,'runtime_use_cache':use_cache,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        write(dest/'attempt.json',base_record)
        if initial>cfg['max_input_tokens']:
            write(dest/'episode.json',{**base_record,'excluded_reason':'input too long; no truncation','generated_token_ids':[]});continue
        with torch.no_grad():
            for step in range(cfg['max_new_tokens']):
                t=time.time()
                output=model(input_ids=ids if past is None else ids[:,-1:],attention_mask=torch.ones_like(ids),past_key_values=past,use_cache=use_cache)
                logits=output.logits[:,-1].float()
                if use_cache:past=output.past_key_values
                del output
                probs=torch.softmax(logits/cfg['temperature'],dim=-1)
                nxt=torch.multinomial(probs,1)
                if use_cache and (step%32==0 or nxt.item()==tok.eos_token_id or step==cfg['max_new_tokens']-1):
                    live=dict(captures)
                    replay=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False).logits[:,-1].float()
                    logit_error=(replay-logits).abs().max().item()
                    residual_error=max(((captures[l]-live[l]).square().mean().sqrt()/live[l].square().mean().sqrt().clamp_min(1e-8)).item() for l in live)
                    parity_checks.append({'step':step,'max_logit_error':logit_error,'max_residual_relative_rms_error':residual_error})
                    captures.update(live);del replay
                    if logit_error>.001 or residual_error>.00001:
                        write(dest/'cache-parity-failure.json',{'episode_id':ep['episode_id'],'check':parity_checks[-1],'prefix_ids':ids[0].tolist(),'generated_token_ids':samples,'disposition':'discard cached attempt; restart entire episode uncached with same seed'})
                        write(dest/'discarded-cached-attempt.json',base_record)
                        failed=True
                        print(json.dumps({'episode_id':ep['episode_id'],'cache_fallback':parity_checks[-1]}),flush=True)
                        break
                for layer in states:states[layer].append(captures[layer])
                token=nxt.item();samples.append(token);ids=torch.cat([ids,nxt],dim=1);step_seconds.append(time.time()-t)
                if step%64==0:write(OUT/'progress.json',{'episode_id':ep['episode_id'],'generated_tokens':len(samples),'elapsed_seconds':time.time()-started})
                if token==tok.eos_token_id:break
        if failed:
            del past,states;torch.cuda.empty_cache();queue.append(ep);continue
        tensors={f'layer_{i}':torch.cat(xs).contiguous() for i,xs in states.items()}
        save_file(tensors,str(dest/'activations.safetensors'),metadata={'hook':'post-block residual','position':'last available state before each sampled token','configuration_sha256':cfg_hash})
        record={**base_record,'generated_token_ids':samples,'generated_text':tok.decode(samples),'stop_reason':'eos' if samples[-1]==tok.eos_token_id else 'token_limit','elapsed_seconds':time.time()-started,'step_seconds':step_seconds,'cache_parity_checks':parity_checks,'activation_sha256':hashlib.sha256((dest/'activations.safetensors').read_bytes()).hexdigest(),'peak_cuda_bytes':torch.cuda.max_memory_allocated(),'external_execution':'not yet performed','label':None}
        write(dest/'episode.json',record);print(json.dumps({'episode_id':ep['episode_id'],'tokens':len(samples),'stop_reason':record['stop_reason'],'seconds':record['elapsed_seconds']}),flush=True)
    write(OUT/'complete.json',{'configuration_sha256':cfg_hash,'episodes':len(assigned),'shard_index':shard_index,'shard_count':shard_count,'labels':'pending external execution and blinded adjudication'})
if __name__=='__main__':
    try:main()
    except Exception:
        (OUT/'error.txt').write_text(traceback.format_exc());raise
