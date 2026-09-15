"""Trusted CPU review queue independent of generation/fit collection and laptop sleep."""
import json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.update(json.loads(Path('/workspace/private/controller-credentials.json').read_text()))
folder=ROOT/'runs/fresh';folder.mkdir(parents=True,exist_ok=True)
import fcntl
lock=(folder/'loop.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
while True:
 if any(folder.glob('*/episode.json')):
  with (folder/'review-console.log').open('a') as log:result=subprocess.run(['/workspace/work/wasm-venv/bin/python',str(ROOT/'scripts/review_batch.py'),str(folder),'--workers','12'],stdout=log,stderr=log,timeout=10800)
  if result.returncode:print('review batch exit',result.returncode,flush=True)
  elif all((ROOT/f'runs/controller/fresh-{i}-complete.json').exists() for i in range(4)):
   summary=json.loads((folder/'review-summary.json').read_text());cfg=json.loads((ROOT/'configs/fresh-v1.json').read_text())
   if summary['completed_episodes']==len(cfg['episodes']) and not any(r['status'] in ['wait_for_valid_activation_shard','audit_error','review_error'] for r in summary['rows']):
    (folder/'review-complete.json').write_text(json.dumps({'episodes':summary['completed_episodes'],'scope':'blinded external labels; no detector test results exposed'})+'\n');break
 time.sleep(60)
