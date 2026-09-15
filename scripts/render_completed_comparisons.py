"""Render scientific figures once each independently computed comparison finishes."""
import fcntl, json, time
from pathlib import Path
from fresh_scoring_loop import run
ROOT=Path(__file__).resolve().parents[1]

def main():
    folder=ROOT/'runs/controller';folder.mkdir(parents=True,exist_ok=True)
    lock=(folder/'comparison-figures.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stages=[('fresh-scoring-complete.json','primary',0),('template-challenge-scoring-complete.json','template-challenge',0),('earlier-position-scoring-complete.json','primary',32),('earlier-position-scoring-complete.json','primary',64)]
    while stages:
        pending=[]
        for marker,scope,offset in stages:
            if not (folder/marker).exists():pending.append((marker,scope,offset));continue
            if offset:
                support=ROOT/f'reports/final-comparison-offset{offset}/support.json'
                if not json.loads(support.read_text())['train_validation_support']:continue
            run('plot_comparison.py','--scope',scope,'--offset',str(offset))
        stages=pending
        if stages:time.sleep(60)
    (folder/'comparison-figures-complete.json').write_text(json.dumps({'status':'completed; unsupported offsets skipped explicitly'})+'\n')

if __name__=='__main__':main()
