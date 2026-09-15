"""Collect opposite-order helper; form a fixed-priority union after writers stop."""
import fcntl,hashlib,json,os,shutil,signal,subprocess,time
from pathlib import Path
from runpod_control import api
ROOT=Path(__file__).resolve().parents[1];os.environ.update(json.loads(Path('/workspace/private/controller-credentials.json').read_text()))
lock=(ROOT/'runs/honest-helper.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
helper=ROOT/'runs/secondary-honest-helper';helper.mkdir(exist_ok=True);original=ROOT/'runs/secondary-honest'
cfgp=ROOT/'configs/secondary-honest-v1.json';identity=ROOT/'configs/secondary-honest-identity.json';cfg=json.loads(cfgp.read_text());ids={e['episode_id'] for e in cfg['episodes']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verified(folder):
 result={}
 for ep in folder.glob('*/episode.json'):
  x=json.loads(ep.read_text());assert x['episode_id'] in ids and x['config_sha256']==sha(cfgp) and x['identity_sha256']==sha(identity)
  act=ep.with_name('activations.safetensors')
  if 'activation_sha256' in x and (not act.exists() or sha(act)!=x['activation_sha256']):continue
  result[x['episode_id']]=ep.parent
 return result
hp=json.loads((ROOT/'runs/pod-honest-helper.json').read_text())['pod'];op=json.loads((ROOT/'runs/pod-secondary-honest.json').read_text())['pod'];assert hp['publicIp'] and hp['portMappings']
transport=f"ssh -i /workspace/private/pod_ed25519 -o UserKnownHostsFile=/workspace/private/known_hosts -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -p {hp['portMappings']['22']}"
end=time.monotonic()+7500
while time.monotonic()<end:
 r=subprocess.run(['rsync','-rt','--timeout=60','-e',transport,f"root@{hp['publicIp']}:/workspace/jlens-research/runs/secondary-honest/",str(helper)+'/'],capture_output=True,text=True)
 if r.returncode:(helper/'collection-error.txt').write_text(r.stderr);time.sleep(30);continue
 ov=verified(original);hv=verified(helper);union=set(ov)|set(hv)
 (ROOT/'runs/honest-helper-progress.json').write_text(json.dumps({'original':len(ov),'helper':len(hv),'union':len(union),'expected':len(ids),'at':time.time()})+'\n')
 if union==ids:break
 time.sleep(30)
else:raise RuntimeError('Helper deadline; preserve independent snapshots and inspect')
# Stop compute before merging; original records win whenever available in final CPU snapshot.
for pod in [hp,op]:
 if api('pods/'+pod['id'])['desiredStatus']=='RUNNING':api('pods/'+pod['id']+'/stop','POST')
if (original/'collection-complete.json').exists():
 (helper/'helper-unused.json').write_text(json.dumps({'reason':'Original canonical run already complete; helper snapshots retained'})+'\n');raise SystemExit(0)
# Stop only the CPU writer whose identity was recorded at launch, then let its children finish.
pid=int(os.environ['CONTROL_SUPERVISOR_PID']);proc=Path(f'/proc/{pid}');assert b'supervise_model_controls.py'in (proc/'cmdline').read_bytes()
def process_table():
 table={}
 for p in Path('/proc').iterdir():
  if p.name.isdigit():
   try:
    s=(p/'stat').read_text().split()
    if s[2]!='Z':table[int(p.name)]=(int(s[3]),s[21])
   except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 return table
table=process_table();desc={pid}
while True:
 new=desc|{p for p,(parent,_) in table.items() if parent in desc}
 if new==desc:break
 desc=new
children={p:table[p][1] for p in desc if p!=pid};os.kill(pid,signal.SIGTERM)
limit=time.monotonic()+600
while True:
 table=process_table();live=[p for p,start in children.items() if p in table and table[p][1]==start]
 if not live:break
 if time.monotonic()>limit:raise RuntimeError('Old collector children still live; no merge performed')
 time.sleep(2)
# Resume collection for the independent base worker without writing the honest directory.
with (ROOT/'runs/secondary-base-controller.log').open('a') as log:
 child=subprocess.Popen(['/workspace/probe-venv/bin/python','-u','scripts/supervise_model_controls.py'],cwd=ROOT,env={**os.environ,'CONTROL_ROLES':'base'},stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 (ROOT/'runs/secondary-base-controller-pid.json').write_text(json.dumps({'pid':child.pid})+'\n')
ov=verified(original);hv=verified(helper);assert set(ov)|set(hv)==ids
archive=ROOT/'runs/secondary-honest-original-snapshot';assert not archive.exists();original.rename(archive);original.mkdir()
for name in ['model-inputs.json','tokenizer-audit.json']:
 if (archive/name).exists():shutil.copy2(archive/name,original/name)
selection=[];duplicates=[]
for eid in sorted(ids):
 source=archive/eid if eid in ov else helper/eid;shutil.copytree(source,original/eid)
 selection.append({'episode_id':eid,'source':str(source.relative_to(ROOT)),'episode_sha256':sha(source/'episode.json')})
 if eid in ov and eid in hv:
  a=json.loads((archive/eid/'episode.json').read_text());b=json.loads((helper/eid/'episode.json').read_text());duplicates.append({'episode_id':eid,'same_tokens':a['generated_token_ids']==b['generated_token_ids'],'same_activations':a.get('activation_sha256')==b.get('activation_sha256'),'original_sha256':sha(archive/eid/'episode.json'),'helper_sha256':sha(helper/eid/'episode.json')})
assert set(verified(original))==ids
(original/'complete.json').write_text(json.dumps({'episodes':45,'producer':'fixed-priority verified union, not single-generator completion','selection':selection,'duplicates':duplicates,'scope':'Original CPU-snapshot records preferred without reading outcomes; both physical snapshots retained'},indent=2)+'\n')
with (original/'review-console.log').open('a') as log:subprocess.run(['/workspace/probe-venv/bin/python','scripts/review_model_controls.py',str(original),'--workers','6'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
(original/'collection-complete.json').write_text(json.dumps({'episodes':45,'verified_activation_files':45,'model_inputs_sha256':sha(original/'model-inputs.json'),'union_manifest_sha256':sha(original/'complete.json'),'scope':'Original/helper union archived and verified; any unavailable behavioral judgments remain explicit'})+'\n')
print('Honest union complete; compute stopped; original/helper snapshots retained',flush=True)
