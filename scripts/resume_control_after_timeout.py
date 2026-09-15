"""Resume only a verified timed-out control process, never a live or failed model."""
import argparse,hashlib,json,os,shutil,subprocess,time,datetime
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('role',choices=['base','honest']);p.add_argument('pid',type=int);a=p.parse_args();ROOT=Path(__file__).resolve().parents[1];out=ROOT/f'runs/secondary-{a.role}'
proc=Path(f'/proc/{a.pid}');cmd=(proc/'cmdline').read_bytes();assert b'behavior_model_controls.py'in cmd
start=(proc/'stat').read_text().split()[21];uptime=float(Path('/proc/uptime').read_text().split()[0]);elapsed=uptime-float(start)/os.sysconf('SC_CLK_TCK');start_wall=time.time()-elapsed
(out/'continuation-watch.json').write_text(json.dumps({'pid':a.pid,'proc_start_ticks':start,'verified_cmdline_sha256':hashlib.sha256(cmd).hexdigest(),'started_wall':start_wall})+'\n')
while proc.exists() and (proc/'stat').read_text().split()[21]==start:time.sleep(30)
if (out/'complete.json').exists():raise SystemExit(0)
assert time.time()-start_wall>=6500,'Original process ended before timeout; inspect rather than restart'
assert not (out/'error.txt').exists(),'Runtime error needs diagnosis; do not blindly restart'
for other in Path('/proc').iterdir():
 if other.name.isdigit():
  try:c=(other/'cmdline').read_bytes()
  except (FileNotFoundError,PermissionError,ProcessLookupError):continue
  assert not (b'python' in c and b'scripts/behavior_model_controls.py' in c),'Another model process is alive'
for ep in out.glob('*/attempt.json'):
 if not (ep.parent/'episode.json').exists():
  archive=ep.parent/'timeout-archive';archive.mkdir(exist_ok=True)
  for f in ep.parent.iterdir():
   if f.is_file():shutil.copy2(f,archive/f.name)
budget=json.loads((ROOT/'runs/control-runtime-budget.json').read_text());deadline=datetime.datetime.fromisoformat(budget['deadlines'][a.role]).timestamp();seconds=int(deadline-time.time()-120);assert seconds>0
with (out/'continuation-console.log').open('a') as log:
 env={**os.environ,'IDENTITY_CONFIG':f'configs/secondary-{a.role}-identity.json','BEHAVIOR_CONFIG':f'configs/secondary-{a.role}-v1.json','BEHAVIOR_OUTPUT':f'runs/secondary-{a.role}'}
 r=subprocess.run(['timeout','--kill-after=60',str(seconds),'/workspace/jlens-venv/bin/python','-u','scripts/behavior_model_controls.py'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
(out/'continuation-result.json').write_text(json.dumps({'returncode':r.returncode,'seconds_allowed':seconds})+'\n')
