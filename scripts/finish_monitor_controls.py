"""Wait for verified monitor collection, then apply frozen comparison stages."""
import fcntl,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
lock=(ROOT/'runs/monitor-finalize.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
end=time.monotonic()+8000
while not (ROOT/'runs/monitor-collection-complete.json').exists():
 if time.monotonic()>end:raise RuntimeError('Monitor collection wait expired; inspect live workers')
 time.sleep(30)
for command in [['prepare_monitor_assembly.py'],['assemble_monitor_controls.py'],['interpret_monitor_controls.py','--phase','test'],['evaluate_monitor_controls.py']]:
 subprocess.run(['/workspace/probe-venv/bin/python','-u','scripts/'+command[0],*command[1:]],cwd=ROOT,check=True)
print('Monitor comparison complete',flush=True)
