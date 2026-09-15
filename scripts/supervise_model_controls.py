"""Cloud collection/review for bounded secondary controls; no guest credentials."""
import concurrent.futures,fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
from runpod_control import api
ROOT=Path(__file__).resolve().parents[1]
os.environ.update(json.loads(Path('/workspace/private/controller-credentials.json').read_text()))
PRIVATE=Path('/workspace/private')
lock=(ROOT/'runs/secondary-controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def work(role):
 state=json.loads((ROOT/f'runs/pod-secondary-{role}.json').read_text());pod=state['pod'];out=ROOT/f'runs/secondary-{role}';out.mkdir(exist_ok=True)
 ip=pod['publicIp'];port=pod['portMappings']['22'];transport=f'ssh -i {PRIVATE}/pod_ed25519 -o UserKnownHostsFile={PRIVATE}/known_hosts -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -p {port}'
 deadline=time.monotonic()+15000
 while time.monotonic()<deadline:
  result=subprocess.run(['rsync','-rt','--timeout=60','-e',transport,f'root@{ip}:/workspace/jlens-research/runs/secondary-{role}/',str(out)+'/'],capture_output=True,text=True)
  if result.returncode:
   (out/'collection-error.txt').write_text(result.stderr);time.sleep(30);continue
  eps=list(out.glob('*/episode.json'))
  if eps:
   with (out/'review-console.log').open('a') as log:
    p=subprocess.run(['/workspace/probe-venv/bin/python','scripts/review_model_controls.py',str(out),'--workers','6'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
   if p.returncode:(out/'review-process-error.json').write_text(json.dumps({'returncode':p.returncode}))
  if (out/'complete.json').exists():
   expected=json.loads((ROOT/f'configs/secondary-{role}-v1.json').read_text())['episodes']
   assert len(eps)==len(expected)
   checks=[]
   for ep in eps:
    record=json.loads(ep.read_text())
    if 'activation_sha256' in record:
     act=ep.parent/'activations.safetensors';assert hashlib.sha256(act.read_bytes()).hexdigest()==record['activation_sha256'];checks.append(record['episode_id'])
   report={'episodes':len(eps),'verified_activation_files':len(checks),'model_inputs_sha256':hashlib.sha256((out/'model-inputs.json').read_bytes()).hexdigest(),'scope':'Cloud archive validated; review failures, if any, remain separate'}
   (out/'collection-complete.json').write_text(json.dumps(report,indent=2)+'\n')
   current=api('pods/'+pod['id'])
   if current['desiredStatus']=='RUNNING':api('pods/'+pod['id']+'/stop','POST')
   print(json.dumps({'role':role,'collected':len(eps),'gpu_stopped':True}),flush=True);return
  if (out/'error.txt').exists():
   print(json.dumps({'role':role,'generation_error':True}),flush=True);return
  time.sleep(30)
 raise RuntimeError('Collection deadline; cloud watchdog remains authoritative')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(work,['base','honest']))
