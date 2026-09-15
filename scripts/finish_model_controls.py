"""Run descriptive analysis once both control archives are verified."""
import fcntl,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
lock=(ROOT/'runs/secondary-analysis.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
end=time.monotonic()+7500
while not all((ROOT/f'runs/secondary-{role}/collection-complete.json').exists() for role in ('base','honest')):
 if time.monotonic()>end:raise RuntimeError('Control collection timeout; inspect live state')
 time.sleep(30)
subprocess.run(['/workspace/probe-venv/bin/python','scripts/analyze_model_controls.py'],cwd=ROOT,check=True)
