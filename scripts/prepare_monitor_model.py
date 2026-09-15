"""Pinned primary model download for the separate monitor-control worker."""
import hashlib,json
from pathlib import Path
from huggingface_hub import snapshot_download
ROOT=Path(__file__).resolve().parents[1];cfg=json.loads((ROOT/'configs/identity-fp32.json').read_text());hashes={}
for role in ('base','adapter'):
 spec=cfg[role];p=Path(snapshot_download(spec['repo'],revision=spec['revision'],cache_dir='/workspace/hf-cache',allow_patterns=['*.safetensors','config.json','adapter_config.json','model.safetensors.index.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','generation_config.json','chat_template.jinja']))
 for f in sorted(p.iterdir()):
  if f.is_file():
   h=hashlib.sha256()
   with f.open('rb') as stream:
    for b in iter(lambda:stream.read(8*1024*1024),b''):h.update(b)
   hashes[role+'/'+f.name]={'sha256':h.hexdigest(),'bytes':f.stat().st_size}
(ROOT/'runs/monitor-model-inputs.json').write_text(json.dumps({'identity_sha256':hashlib.sha256((ROOT/'configs/identity-fp32.json').read_bytes()).hexdigest(),'files':hashes},indent=2)+'\n')
