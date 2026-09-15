"""Score a separate template-shift challenge only with primary locked detectors."""
import fcntl,json,time
from fresh_scoring_loop import ROOT,run

def main():
    folder=ROOT/'runs/controller'
    lock=(folder/'template-challenge-scoring.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    prerequisites=[folder/'fresh-scoring-complete.json',ROOT/'runs/template-challenge/review-complete.json']
    prerequisites += [folder/f'challenge-processed-{i}-complete.json' for i in range(4)]
    while not all(p.exists() for p in prerequisites):time.sleep(60)
    if not (ROOT/'runs/template-challenge-assembled/complete.json').exists():
        run('assemble_fresh.py','--dataset','template-challenge')
    done=ROOT/'runs/template-challenge-jview-test/complete.json'
    if not done.exists() or json.loads(done.read_text())['errors']:
        run('interpret_fresh.py','--phase','test','--dataset','template-challenge','--workers','12')
    assert not json.loads(done.read_text())['errors']
    run('evaluate_fresh.py','--dataset','template-challenge')
    (folder/'template-challenge-scoring-complete.json').write_text(json.dumps({'scope':'Frozen template-shift challenge scored with primary weights/thresholds; matched-pair audit and final report still required'})+'\n')

if __name__=='__main__':main()
