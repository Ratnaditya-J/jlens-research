"""Stage-zero identity/derivative pilot; no behavioral conclusions are drawn."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import time
import os

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/os.environ.get('IDENTITY_CONFIG','configs/identity.json')
OUT=ROOT/os.environ.get('IDENTITY_OUTPUT','runs/identity')
OUT.mkdir(parents=True,exist_ok=True)

def write(name,data):
    p=OUT/name; tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(p)

def main():
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import PeftModel
    cfg=json.loads(CONFIG.read_text())
    assert all(len(cfg[k]['revision'])==40 for k in ['base','adapter'])
    started=time.time();torch.manual_seed(cfg['seed'])
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    report={'kind':'identity_pilot','scientific_evidence':False,'configuration':cfg,'config_sha256':hashlib.sha256(CONFIG.read_bytes()).hexdigest(),'python':platform.python_version(),'gpu':torch.cuda.get_device_name(0),'cuda':torch.version.cuda,'versions':{p:importlib.metadata.version(p) for p in ['torch','transformers','peft','huggingface-hub','safetensors']},'stage':'download'}
    write('progress.json',report)
    locations={}
    for role in ['base','adapter']:
        entry=cfg[role]
        locations[role]=snapshot_download(entry['repo'],revision=entry['revision'],allow_patterns=['*.safetensors','config.json','adapter_config.json','model.safetensors.index.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','generation_config.json','chat_template.jinja','README.md','LICENSE*','NOTICE*','USE_POLICY*'],cache_dir='/workspace/hf-cache')
    hashes={}
    for role,location in locations.items():
        for p in sorted(Path(location).iterdir()):
            if p.is_file():
                h=hashlib.sha256()
                with p.open('rb') as f:
                    for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
                hashes[f'{role}/{p.name}']={'sha256':h.hexdigest(),'bytes':p.stat().st_size}
    write('download-hashes.json',hashes)
    report['stage']='load';report['download_seconds']=time.time()-started;write('progress.json',report)
    tok=AutoTokenizer.from_pretrained(locations['base'],trust_remote_code=False)
    hf=AutoModelForCausalLM.from_pretrained(locations['base'],dtype=getattr(torch,cfg['dtype']),device_map={'':'cuda:0'},attn_implementation='eager',trust_remote_code=False,use_safetensors=True)
    model=PeftModel.from_pretrained(hf,locations['adapter'],is_trainable=False).eval()
    for p in model.parameters():p.requires_grad_(False)
    base=model.get_base_model()
    lora=[n for n,p in model.named_parameters() if 'lora_' in n]
    report['lora_tensor_count']=len(lora);report['lora_tensor_names']=lora
    assert len(lora)==24*4*2, f'Unexpected LoRA key count: {len(lora)}'
    assert tok.chat_template,'Missing chat template'
    report['chat_template_sha256']=hashlib.sha256(tok.chat_template.encode()).hexdigest()
    messages=[{'role':'user','content':'What is two plus two? Answer briefly.'}]
    ids=tok.apply_chat_template(messages,add_generation_prompt=True,return_tensors='pt').to('cuda')
    report['input_ids']=ids[0].tolist()
    captures={}
    handles=[]
    def hook(i):
        def record(m,args,out):captures[i]=(out[0] if isinstance(out,tuple) else out).detach().clone()
        return record
    for i,block in enumerate(base.model.layers): handles.append(block.register_forward_hook(hook(i)))
    with torch.no_grad():
        on=model(ids,use_cache=False).logits.float()
        residuals={i:h.clone() for i,h in captures.items()}
        manual=base.lm_head(base.model.norm(residuals[23])).float()
    for h in handles:h.remove()
    with torch.no_grad():
        clean=model(ids,use_cache=False).logits.float()
        with model.disable_adapter(): off=model(ids,use_cache=False).logits.float()
    report['hook_max_logit_error']=(on-clean).abs().max().item()
    report['unembedding_max_logit_error']=(on-manual).abs().max().item()
    report['lora_on_off_max_logit_difference']=(on-off).abs().max().item()
    report['lora_on_off_mean_logit_difference']=(on-off).abs().mean().item()
    report['residual_shapes']={i:list(h.shape) for i,h in residuals.items()}
    assert report['hook_max_logit_error']==0
    assert report['unembedding_max_logit_error']==0
    assert report['lora_on_off_max_logit_difference']>0
    # Live KV-cache decoding versus teacher-forced replay, same tokens.
    with torch.no_grad():
        cached=model(ids[:,:-1],use_cache=True)
        step=model(ids[:,-1:],past_key_values=cached.past_key_values,use_cache=True).logits[:,-1].float()
        report['cached_replay_max_logit_error']=(step-on[:,-1]).abs().max().item()
        report['cached_replay_mean_logit_error']=(step-on[:,-1]).abs().mean().item()
        generated=model.generate(ids,max_new_tokens=32,do_sample=False,pad_token_id=tok.eos_token_id)
    report['smoke_generation_ids']=generated[0].tolist()
    report['smoke_generation_text']=tok.decode(generated[0,ids.shape[1]:])
    del cached,step,on,off,manual,clean,residuals,captures
    torch.cuda.empty_cache()
    # Differentiate final hidden state through the last block from layer 22.
    x=base.model.embed_tokens(ids).detach().requires_grad_(True)
    retained={}
    def retain(m,args,out):retained['h']=out[0] if isinstance(out,tuple) else out
    handle=base.model.layers[22].register_forward_hook(retain)
    y=base.model(inputs_embeds=x,use_cache=False).last_hidden_state
    handle.remove()
    cotangent=torch.randn(y[:,-1].shape,device='cuda',dtype=torch.float32)
    scalar=(y[:,-1].float()*cotangent).sum()
    grad=torch.autograd.grad(scalar,retained['h'])[0].float()
    direction=torch.randn_like(grad);direction/=direction.square().mean().sqrt()
    predicted=(grad*direction).sum().item()
    report['derivative_finite']=bool(torch.isfinite(grad).all())
    report['derivative_norm']=grad.norm().item();report['directional_derivative']=predicted
    del y,scalar,x,grad,retained
    torch.cuda.empty_cache()
    sweep=[]
    for eps in [0.01,0.03,0.1,0.3]:
        values=[]
        for sign in [-1,1]:
            def perturb(m,args,out):
                if isinstance(out,tuple):return (out[0]+(sign*eps*direction).to(out[0].dtype),)+out[1:]
                return out+(sign*eps*direction).to(out.dtype)
            h=base.model.layers[22].register_forward_hook(perturb)
            with torch.no_grad():
                yy=base.model(input_ids=ids,use_cache=False).last_hidden_state
                values.append((yy[:,-1].float()*cotangent).sum().item())
            h.remove()
        finite=(values[1]-values[0])/(2*eps)
        sweep.append({'epsilon':eps,'finite_difference':finite,'relative_error':abs(finite-predicted)/max(abs(finite),abs(predicted),1e-8)})
    report['finite_difference_sweep']=sweep
    report['peak_cuda_bytes']=torch.cuda.max_memory_allocated()
    report['elapsed_seconds']=time.time()-started
    report['stage']='completed'
    report['gate']={'identity':'pass','finite_gradient':'pass' if report['derivative_finite'] else 'fail','numerical_tolerance':'requires precision-pilot analysis; BF16 finite differences and MoE route changes can dominate','behavior_confirmation':'not attempted','lens_validity':'not established'}
    write('report.json',report);write('progress.json',report)
    (OUT/'pip-freeze.txt').write_text(subprocess.check_output(['python','-m','pip','freeze'],text=True))
    print(json.dumps({k:report[k] for k in ['stage','gate','elapsed_seconds','peak_cuda_bytes','finite_difference_sweep']}),flush=True)

if __name__=='__main__':
    try:main()
    except Exception:
        import traceback
        (OUT/'error.txt').write_text(traceback.format_exc())
        raise
