"""CPU stage sequencer: preserve calibration lock before any held-out scoring."""
import fcntl
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = '/workspace/probe-venv/bin/python'

def run(script, *args):
    log = ROOT / 'runs/controller/fresh-scoring.log'
    with log.open('a') as stream:
        result = subprocess.run([PYTHON, str(ROOT / 'scripts' / script), *args],
                                stdout=stream, stderr=stream)
    if result.returncode:
        raise RuntimeError(f'{script} exited {result.returncode}; inspect preserved log')

def main():
    folder = ROOT / 'runs/controller'
    folder.mkdir(parents=True, exist_ok=True)
    lock = (folder / 'fresh-scoring.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    prerequisites = [ROOT / 'runs/fresh/review-complete.json'] + [
        ROOT / f'runs/controller/processed-{i}-complete.json' for i in range(4)]
    while not all(p.exists() for p in prerequisites):
        time.sleep(60)
    if not (ROOT / 'runs/fresh-assembled/complete.json').exists():
        run('assemble_fresh.py')
    for phase in ['validation', 'test']:
        if phase == 'test':
            if not (ROOT / 'runs/fresh-calibration/lock.json').exists():
                run('calibrate_fresh.py')
            assert (ROOT / 'runs/fresh-calibration/lock.json').exists()
            if not (ROOT / 'runs/supervised-jspace/lock.json').exists():
                run('supervised_jspace.py', 'calibrate')
        complete = ROOT / f'runs/fresh-jview-{phase}/complete.json'
        if not complete.exists() or json.loads(complete.read_text())['errors']:
            run('interpret_fresh.py', '--phase', phase, '--workers', '12')
        assert not json.loads(complete.read_text())['errors'], 'Incomplete reviewer results'
    run('evaluate_fresh.py')
    run('supervised_jspace.py', 'evaluate')
    report = ROOT / 'reports/final-comparison/summary.json'
    (folder / 'fresh-scoring-complete.json').write_text(json.dumps({
        'summary_sha256': hashlib.sha256(report.read_bytes()).hexdigest(),
        'scope': 'Primary held-out scoring complete; final research report and audit still required'
    }, indent=2) + '\n')

if __name__ == '__main__':
    main()
