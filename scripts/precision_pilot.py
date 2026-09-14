"""Isolated FP32 suffix derivative diagnostic, not a new behavioral checkpoint."""
import json,time
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import PeftModel
from huggingface_hub import snapshot_download

root=Path(__file__).resolve().parents[1];out=root/'runs/precision';out.mkdir(parents=True,exist_ok=True)
torch.manual_seed(271828);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
cfg=json.loads((root/'configs/identity.json').read_text()); paths={}
for role in ['base','adapter']:
    paths[role]=snapshot_download(cfg[role]['repo'],revision=cfg[role]['revision'],cache_dir='/workspace/hf-cache',local_files_only=True)
tok=AutoTokenizer.from_pretrained(paths['base'])
hf=AutoModelForCausalLM.from_pretrained(paths['base'],dtype=torch.bfloat16,device_map={'':'cuda'},attn_implementation='eager')
model=PeftModel.from_pretrained(hf,paths['adapter']).eval()
for p in model.parameters():p.requires_grad_(False)
base=model.get_base_model();block=base.model.layers[23];saved={}
def capture(m,args,kwargs):saved.update(args=args,kwargs=kwargs)
hook=block.register_forward_pre_hook(capture,with_kwargs=True)
ids=tok.apply_chat_template([{'role':'user','content':'What is two plus two? Answer briefly.'}],add_generation_prompt=True,return_tensors='pt').cuda()
with torch.no_grad():base.model(ids,use_cache=False)
hook.remove()
def cast(v):
    if isinstance(v,torch.Tensor):return v.float() if v.is_floating_point() else v
    if isinstance(v,tuple):return tuple(cast(x) for x in v)
    if isinstance(v,dict):return {k:cast(x) for k,x in v.items()}
    return v
args=cast(saved['args']);kwargs=cast(saved['kwargs'])
x=(args[0] if args else kwargs.pop('hidden_states')).detach().requires_grad_(True)
tail=args[1:];block.float()
routes=[]
route_hook=block.mlp.router.register_forward_hook(lambda m,a,o:routes.append(o[1].detach().sort(dim=-1).values.clone()))
def forward(z):return block(z,*tail,**kwargs)
y=forward(x);reference_routes=routes[-1]
v=torch.randn_like(y[:,-1]);d=torch.zeros_like(x);d[:,-1]=torch.randn_like(x[:,-1]);d/=d[:,-1].square().mean().sqrt()
g=torch.autograd.grad((y[:,-1].double()*v.double()).sum(),x)[0]
pred=(g.double()*d.double()).sum().item();results=[]
for eps in [0.0003,0.001,0.003,0.01,0.03]:
    vals=[];changed=[]
    for sign in [-1,1]:
        with torch.no_grad():yy=forward(x.detach()+sign*eps*d)
        vals.append((yy[:,-1].double()*v.double()).sum().item());changed.append(int((routes[-1]!=reference_routes).any(dim=-1).sum()))
    fd=(vals[1]-vals[0])/(2*eps)
    results.append({'epsilon':eps,'autodiff':pred,'finite_difference':fd,'relative_error':abs(fd-pred)/max(abs(fd),abs(pred),1e-8),'changed_routing_tokens':changed})
report={'diagnostic':'FP32 last-block suffix at BF16 checkpoint residual; not behavioral execution','tf32':False,'source_layer':22,'target_layer':23,'direction_support':'last token only','rows':results,'gate':'pass' if any(r['relative_error']<0.02 and sum(r['changed_routing_tokens'])==0 for r in results) else 'fail','criterion':'At least one epsilon has <2% relative error with unchanged expert sets; inspect full sweep','peak_cuda_bytes':torch.cuda.max_memory_allocated()}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
