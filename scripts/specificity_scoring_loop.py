"""Secondary authorized controls use the primary frozen calibration unchanged."""
import fcntl,hashlib,json,time
from pathlib import Path
from fresh_scoring_loop import run
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'runs/controller';folder.mkdir(parents=True,exist_ok=True)
    guard=(folder/'specificity-scoring.lock').open('a');fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
    prerequisites=[folder/'fresh-scoring-complete.json',ROOT/'runs/specificity-controls/review-complete.json']+[folder/f'specificity-processed-{i}-complete.json' for i in range(4)]
    while not all(p.exists() for p in prerequisites):time.sleep(60)
    args=['--dataset','specificity-controls']
    if not (ROOT/'runs/specificity-controls-assembled/complete.json').exists():run('assemble_fresh.py',*args)
    done=ROOT/'runs/specificity-controls-jview-test/complete.json'
    if not done.exists() or json.loads(done.read_text())['errors']:run('interpret_fresh.py','--phase','test',*args)
    assert not json.loads(done.read_text())['errors']
    run('evaluate_fresh.py',*args)
    summary=ROOT/'reports/specificity-controls-comparison/summary.json'
    (folder/'specificity-scoring-complete.json').write_text(json.dumps({'summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),'scope':'Secondary controls scored with unchanged primary model/thresholds; not a new calibration'})+'\n')
if __name__=='__main__':main()
