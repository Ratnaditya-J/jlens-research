"""Deploy only control source/configs; provider credentials stay on controller."""
import json,subprocess,time,sys
from pathlib import Path
from runpod_control import api,sanitized
ROOT=Path(__file__).resolve().parents[1]
role=sys.argv[1];assert role in ('base','honest')
state_path=ROOT/f'runs/pod-secondary-{role}.json';state=json.loads(state_path.read_text())
key=str((ROOT/'../../work/private/pod_ed25519').resolve());hosts=str((ROOT/'../../work/private/known_hosts').resolve())
options=['-i',key,'-o','UserKnownHostsFile='+hosts,'-o','StrictHostKeyChecking=accept-new','-o','ConnectTimeout=10']
end=time.monotonic()+900
while time.monotonic()<end:
 p=api('pods/'+state['pod']['id']); port=(p.get('portMappings') or {}).get('22'); ip=p.get('publicIp')
 if ip and port:
  ssh=['ssh',*options,'-p',str(port),'root@'+ip]
  check=subprocess.run(ssh+['mkdir -p /workspace/jlens-research/scripts /workspace/jlens-research/configs /workspace/jlens-research/runs'],capture_output=True)
  if check.returncode==0:break
 time.sleep(10)
else:raise RuntimeError('SSH readiness timeout; pod remains tracked under cloud deadline')
state['pod']=sanitized(p);state_path.write_text(json.dumps(state,indent=2)+'\n')
for folder,files in [('scripts',['prepare_model_control.py','behavior_model_controls.py','bootstrap_model_control.sh']),('configs',[f'secondary-{role}-identity.json',f'secondary-{role}-v1.json'])]:
 subprocess.run(['scp',*options,'-P',str(port),*[str(ROOT/folder/f) for f in files],f'root@{ip}:/workspace/jlens-research/{folder}/'],check=True)
cmd=f'cd /workspace/jlens-research && mkdir -p runs/secondary-{role} && (nohup env CONTROL_ROLE={role} bash scripts/bootstrap_model_control.sh > runs/secondary-{role}/bootstrap.log 2>&1 < /dev/null & echo $! > runs/secondary-{role}/bootstrap.pid)'
subprocess.run(ssh+[cmd],check=True,timeout=30)
print(json.dumps({'role':role,'pod':p['id'],'ip':ip,'port':port,'deployed':True}),flush=True)
