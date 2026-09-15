"""Separate endpoint calibrations on frozen offsets; never reuse onset weights."""
import argparse, fcntl, hashlib, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from fresh_scoring_loop import run

def support(records):
    import numpy as np
    from sklearn.model_selection import GroupKFold
    eligible={s:[r for r in records[s] if r['feature_index'] is not None and r['label'] in ['misaligned','benign']] for s in records}
    counts={s:{k:sum(r['label']==k for r in rs) for k in ['misaligned','benign']} for s,rs in eligible.items()}
    if any(min(v.values())==0 for v in counts.values()):
        return False, counts, 'Training or validation lacks one behavior class'
    y=np.array([r['label']=='misaligned' for r in eligible['train']]);g=np.array([r['family_id'] for r in eligible['train']])
    if len(set(g))<4:
        return False, counts, 'Fewer than four usable training families'
    for train,valid in GroupKFold(n_splits=4).split(np.zeros((len(y),1)), y, g):
        if len(set(y[train]))<2 or len(set(y[valid]))<2:
            return False, counts, 'A frozen grouped training fold lacks one behavior class'
    return True, counts, None

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--wait',action='store_true');args=parser.parse_args()
    folder=ROOT/'runs/controller';folder.mkdir(parents=True,exist_ok=True)
    lock=(folder/'earlier-position-scoring.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if args.wait:
        while not (folder/'fresh-scoring-complete.json').exists():time.sleep(60)
    assert (ROOT/'runs/fresh-calibration/lock.json').exists()
    for offset in [32,64]:
        args=['--offset',str(offset)];stem=f'fresh-offset{offset}'
        data=ROOT/f'runs/{stem}-assembled'
        if not (data/'complete.json').exists():run('assemble_fresh.py',*args)
        records={s:json.loads((data/f'{s}-records.json').read_text()) for s in ['train','validation']}
        enough,counts,reason=support(records)
        out=ROOT/f'reports/final-comparison-offset{offset}';out.mkdir(parents=True,exist_ok=True)
        (out/'support.json').write_text(json.dumps({'offset':offset,'train_validation_support':enough,'counts':counts,'reason':reason},indent=2)+'\n')
        if not enough:continue
        for phase in ['validation','test']:
            if phase=='test' and not (ROOT/f'runs/{stem}-calibration/lock.json').exists():run('calibrate_fresh.py',*args)
            complete=ROOT/f'runs/{stem}-jview-{phase}/complete.json'
            if not complete.exists() or json.loads(complete.read_text())['errors']:
                run('interpret_fresh.py','--phase',phase,*args)
            assert not json.loads(complete.read_text())['errors']
        run('evaluate_fresh.py',*args)
    reports=[ROOT/f'reports/final-comparison-offset{o}' for o in [32,64]]
    (folder/'earlier-position-scoring-complete.json').write_text(json.dumps({
        'files_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for d in reports for p in d.glob('*.json')},
        'scope':'Secondary endpoint scoring finished or explicit insufficient training support reported; not complete detection trajectories'
    },indent=2)+'\n')

if __name__=='__main__':main()
