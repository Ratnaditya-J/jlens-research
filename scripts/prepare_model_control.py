"""Download and hash a pinned secondary model; no generated-code execution."""
import hashlib,json,os,platform,importlib.metadata
from pathlib import Path
from huggingface_hub import snapshot_download
ROOT=Path(__file__).resolve().parents[1]
role=os.environ['CONTROL_ROLE'];assert role in ('base','honest')
cfg=ROOT/f'configs/secondary-{role}-identity.json'; spec=json.loads(cfg.read_text())['model']
prefix=spec.get('subfolder',''); prefix=prefix+'/' if prefix else ''
patterns=[prefix+x for x in ['*.safetensors','config.json','model.safetensors.index.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','generation_config.json','chat_template.jinja']]
p=Path(snapshot_download(spec['repo'],revision=spec['revision'],allow_patterns=patterns,cache_dir='/workspace/hf-cache'))/spec.get('subfolder','')
files={}
for f in sorted(p.iterdir()):
 if f.is_file():
  h=hashlib.sha256()
  with f.open('rb') as s:
   for b in iter(lambda:s.read(8*1024*1024),b''):h.update(b)
  files[f.name]={'sha256':h.hexdigest(),'bytes':f.stat().st_size}
index=json.loads((p/'model.safetensors.index.json').read_text())
assert set(index['weight_map'].values())<=files.keys()
config=json.loads((p/'config.json').read_text());assert config['model_type']=='gpt_oss' and config['hidden_size']==2880 and config['num_hidden_layers']==24
out=ROOT/f'runs/secondary-{role}';out.mkdir(exist_ok=True,parents=True)
(out/'model-inputs.json').write_text(json.dumps({'identity_sha256':hashlib.sha256(cfg.read_bytes()).hexdigest(),'spec':spec,'files':files,'python':platform.python_version(),'versions':{x:importlib.metadata.version(x) for x in ['torch','transformers','huggingface-hub','safetensors']}},indent=2)+'\n')
print('Pinned model inputs verified',role,flush=True)
