"""Decode only the generated prefix permitted by the frozen position manifest."""
import hashlib,json
from pathlib import Path
from transformers import AutoTokenizer
from huggingface_hub import snapshot_download
ROOT=Path(__file__).resolve().parents[1]
identity=json.loads((ROOT/'configs/identity-fp32.json').read_text())['base']
tok=AutoTokenizer.from_pretrained(snapshot_download(identity['repo'],revision=identity['revision'],cache_dir='/workspace/hf-cache',local_files_only=True),trust_remote_code=False)
p=ROOT/'runs/development-positions.json';positions=json.loads(p.read_text());rows=[]
for row in positions['rows']:
 if 'unavailable' in row:continue
 epath=ROOT/'runs/position-input'/row['episode_id']/'episode.json';e=json.loads(epath.read_text());assert hashlib.sha256(epath.read_bytes()).hexdigest()==row['episode_sha256']
 rows.append({'episode_id':row['episode_id'],'prompt':'\n'.join(m['role']+': '+m['content'] for m in e['messages']),'generated_prefix':tok.decode(row['permitted_generated_prefix_ids'])})
(ROOT/'runs/development-permitted-text.json').write_text(json.dumps({'positions_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rows':rows},indent=2)+'\n')
