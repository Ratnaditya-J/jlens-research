"""CPU-only tokenization audit; never changes the running tokenizer."""
import os,json,hashlib,inspect
from pathlib import Path
from transformers import AutoTokenizer
from huggingface_hub import snapshot_download
import transformers.tokenization_utils_fast as fast
ROOT=Path(__file__).resolve().parents[1];role=os.environ['CONTROL_ROLE']
spec=json.loads((ROOT/f'configs/secondary-{role}-identity.json').read_text())['model']
p=Path(snapshot_download(spec['repo'],revision=spec['revision'],cache_dir='/workspace/hf-cache',local_files_only=True))/spec.get('subfolder','')
tok=AutoTokenizer.from_pretrained(p,trust_remote_code=False)
cfg=json.loads((ROOT/f'configs/secondary-{role}-v1.json').read_text())
rows=[{'source_episode_id':e['source_episode_id'],'input_ids':tok.apply_chat_template(e['messages'],add_generation_prompt=True,reasoning_effort=cfg['reasoning_effort'])} for e in cfg['episodes']]
tj=json.loads((p/'tokenizer.json').read_text());s=inspect.getsource(fast);lines=s.splitlines();contexts=[]
for i,line in enumerate(lines):
 if 'incorrect regex' in line:contexts.append('\n'.join(lines[max(0,i-45):i+15]))
result={'role':role,'tokenizer_class':type(tok).__name__,'vocab_size':len(tok),'rows':rows,'pre_tokenizer':tj.get('pre_tokenizer'),'model_sha256':hashlib.sha256(json.dumps(tj.get('model'),sort_keys=True).encode()).hexdigest(),'added_tokens_sha256':hashlib.sha256(json.dumps(tj.get('added_tokens'),sort_keys=True).encode()).hexdigest(),'chat_template_sha256':hashlib.sha256(tok.chat_template.encode()).hexdigest(),'warning_source':contexts,'scope':'Unmodified shipped tokenizer; all frozen control prompt encodings captured; not a universal tokenizer equivalence test'}
(ROOT/f'runs/secondary-{role}/tokenizer-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(role,len(rows),len(tok))
