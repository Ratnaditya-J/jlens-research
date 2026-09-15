"""Deploy only control source/configs; provider credentials stay on controller."""
import json,subprocess,time,sys
from pathlib import Path
from runpod_control import api,sanitized
ROOT=Path(__file__).resolve().parents[1]
role='monitor'
state_path=ROOT/'runs/pod-monitor.json';state=json.loads(state_path.read_text())
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
files_by_folder={'scripts':['prepare_monitor_model.py','behavior_pilot.py','postprocess_fresh.py','gptoss_lens_model.py','bootstrap_monitor_control.sh'],'configs':['identity-fp32.json','monitor-controls-v1.json','jview-interpretation-v1.json'],'src':['positions.py','source_parser.py','AISI-LICENSE'],'runs/fit64-merged':['lens.pt','report.json']}
for folder,files in files_by_folder.items():
 subprocess.run(ssh+['mkdir -p /workspace/jlens-research/'+folder],check=True)
 subprocess.run(['scp',*options,'-P',str(port),*[str(ROOT/folder/f) for f in files],f'root@{ip}:/workspace/jlens-research/{folder}/'],check=True)
transport=' '.join(ssh[:-1])
subprocess.run(['rsync','-rt','--exclude=.git','--exclude=__pycache__','-e',transport,str(ROOT/'../../work/upstream/jacobian-lens')+'/',f'root@{ip}:/workspace/jacobian-lens/'],check=True)
cmd='cd /workspace/jlens-research && (nohup bash scripts/bootstrap_monitor_control.sh > runs/monitor-bootstrap.log 2>&1 < /dev/null & echo $! > runs/monitor-bootstrap.pid)'
subprocess.run(ssh+[cmd],check=True,timeout=30)
print(json.dumps({'pod':p['id'],'ip':ip,'port':port,'deployed':True}),flush=True)
