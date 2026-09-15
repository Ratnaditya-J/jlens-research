"""Archive only pinned native normalization/unembedding for CPU trace display."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    from safetensors import safe_open
    from safetensors.torch import save_file
    cfg=json.loads((ROOT/'configs/identity-fp32.json').read_text());base=cfg['base']
    folder=ROOT/'runs/cpu-readout';folder.mkdir(parents=True,exist_ok=True)
    url=f"https://huggingface.co/{base['repo']}/resolve/{base['revision']}/"
    def fetch(name):
        p=folder/name
        if not p.exists():
            tmp=p.with_suffix(p.suffix+'.partial');urllib.request.urlretrieve(url+name,tmp);tmp.replace(p)
        return p
    indexp=fetch('model.safetensors.index.json');index=json.loads(indexp.read_text())['weight_map']
    configp=fetch('config.json');fetch('tokenizer.json')
    keys=['lm_head.weight','model.norm.weight'];assert 'lm_head.bias' not in index
    tensors={}
    sources={}
    for name in sorted({index[k] for k in keys}):
        p=fetch(name);sources[name]=sha(p)
        with safe_open(p,framework='pt',device='cpu') as reader:
            for key in keys:
                if index[key]==name:tensors[key]=reader.get_tensor(key).contiguous()
    target=folder/'native-readout.safetensors'
    if not target.exists():save_file(tensors,str(target))
    else:
        with safe_open(target,framework='pt',device='cpu') as reader:
            import torch
            for key in keys:assert torch.equal(reader.get_tensor(key),tensors[key])
    sourceurl='https://raw.githubusercontent.com/huggingface/transformers/v4.57.6/src/transformers/models/gpt_oss/modeling_gpt_oss.py'
    source=folder/'modeling_gpt_oss-reference.py'
    if not source.exists():urllib.request.urlretrieve(sourceurl,source)
    report={'base':base,'identity_sha256':sha(ROOT/'configs/identity-fp32.json'),'shards_sha256':sources,'files_sha256':{p.name:sha(p) for p in [target,indexp,configp,folder/'tokenizer.json',source]},'reference_source_url':sourceurl,'script_sha256':sha(Path(__file__)),'scope':'Native base final norm and vocabulary projection only; LoRA targets q/k/v/o, so these weights are unchanged. CPU display parity against existing FP32 GPU readouts still required.'}
    (folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print('CPU readout weights archived',flush=True)
if __name__=='__main__':main()
