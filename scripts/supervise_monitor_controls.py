"""Cloud collection and behavioral review of all four monitor shards."""
import fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
from runpod_control import api
ROOT=Path(__file__).resolve().parents[1]
os.environ.update(json.loads(Path('/workspace/private/controller-credentials.json').read_text()))
lock=(ROOT/'runs/monitor-controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
state=json.loads((ROOT/'runs/pod-monitor.json').read_text());pod=state['pod'];ip=pod['publicIp'];port=pod['portMappings']['22']
transport=f'ssh -i /workspace/private/pod_ed25519 -o UserKnownHostsFile=/workspace/private/known_hosts -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -p {port}'
end=time.monotonic()+7200
while time.monotonic()<end:
 finished=[]
 for shard in range(4):
  for prefix in ('monitor-controls-shard','monitor-controls-processed'):
   out=ROOT/f'runs/{prefix}-{shard}';out.mkdir(exist_ok=True)
   r=subprocess.run(['rsync','-rt','--timeout=60','-e',transport,f'root@{ip}:/workspace/jlens-research/runs/{prefix}-{shard}/',str(out)+'/'],capture_output=True,text=True)
   if r.returncode:(out/'collection-last-error.txt').write_text(r.stderr)
  raw=ROOT/f'runs/monitor-controls-shard-{shard}';processed=ROOT/f'runs/monitor-controls-processed-{shard}'
  if list(raw.glob('*/episode.json')):
   with (raw/'review-console.log').open('a') as log:
    r=subprocess.run(['/workspace/probe-venv/bin/python','scripts/review_monitor_controls.py',str(raw),'--workers','4'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
   if r.returncode:print(json.dumps({'shard':shard,'review_returncode':r.returncode}),flush=True)
  if (processed/'complete.json').exists():
   c=json.loads((processed/'complete.json').read_text());assert c['completed']==c['assigned']==6
   for eid,digest in c['case_complete_sha256'].items():
    p=processed/eid/'complete.json';assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    for name,h in json.loads(p.read_text())['files_sha256'].items():assert hashlib.sha256((p.parent/name).read_bytes()).hexdigest()==h
    ep=raw/eid/'episode.json';record=json.loads(ep.read_text())
    if 'activation_sha256'in record:assert hashlib.sha256((ep.parent/'activations.safetensors').read_bytes()).hexdigest()==record['activation_sha256']
   finished.append(shard)
 (ROOT/'runs/monitor-collection-progress.json').write_text(json.dumps({'verified_processed_shards':finished,'at':time.time()})+'\n')
 if len(finished)==4:
  (ROOT/'runs/monitor-collection-complete.json').write_text(json.dumps({'verified_processed_shards':finished,'episodes':24,'scope':'CPU collected raw and processed artifacts verified; behavioral/J interpretation completeness separate'})+'\n')
  if api('pods/'+pod['id'])['desiredStatus']=='RUNNING':api('pods/'+pod['id']+'/stop','POST')
  print('All monitor raw/processed artifacts collected; GPU stopped',flush=True);break
 time.sleep(30)
else:raise RuntimeError('Collection wait expired; inspect authoritative GPU state and retain artifacts')
