"""Run the prepared reproduction only after the recorded analysis process exits."""
import fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
lock=(ROOT/'runs/model-control-reproduction.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
pid=int(os.environ['CONTROL_ANALYSIS_PID'])
proc=Path(f'/proc/{pid}')
assert b'finish_model_controls.py' in (proc/'cmdline').read_bytes()
start=(proc/'stat').read_text().split()[21]
end=time.monotonic()+9000
while True:
 try:
  fields=(proc/'stat').read_text().split()
  live=fields[21]==start and fields[2]!='Z'
 except (FileNotFoundError,ProcessLookupError):live=False
 if not live:break
 if time.monotonic()>end:raise RuntimeError('Analysis still live at reproduction wait limit; inspect, do not restart')
 time.sleep(30)
for role in ('base','honest'):
 assert (ROOT/f'runs/secondary-{role}/collection-complete.json').exists()
for name in ('summary.json','findings.md'):
 assert (ROOT/'reports/model-controls'/name).exists()
subprocess.run(['/workspace/probe-venv/bin/python','scripts/reproduce_model_controls.py','--destination','/workspace/work/jlens-model-controls-reproduction-20260915'],cwd=ROOT,check=True)
r=json.loads((ROOT/'reports/model-controls-reproduction.json').read_text());assert r['status']=='passed'
for name,h in r['reproduced_outputs_sha256'].items():
 assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
(ROOT/'runs/model-control-reproduction-complete.json').write_text(json.dumps({'status':'passed','at':time.time(),'exact_outputs':r['exact_outputs']})+'\n')
print('Native-control reproduction passed; final local archive and report review remain',flush=True)
