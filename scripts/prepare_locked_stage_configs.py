"""Build reproducible CPU stage plans from already frozen calibration artifacts."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    lockp=ROOT/'runs/fresh-calibration/lock.json';lock=json.loads(lockp.read_text())
    for name,digest in lock['source_hashes'].items():assert sha(ROOT/name)==digest
    for name,digest in lock['artifacts'].items():assert sha(lockp.parent/name)==digest
    def plan(name,stage,script,args,inputs,outputs,scope):
        inputs=set(inputs)|{'configs/identity-fp32.json','scripts/'+script}
        cfg={'stage':stage,'identity_config':'configs/identity-fp32.json','inputs_sha256':{name:sha(ROOT/name) for name in sorted(inputs)},'commands':[{'script':script,'args':args}],'outputs':outputs,'resource_estimate':{'gpu_hours':0,'api_calls':0,'basis':'CPU-only reconstruction from existing frozen artifacts; elapsed time depends on CPU and libraries'},'scope':scope}
        path=ROOT/'configs/stages'/name;path.parent.mkdir(parents=True,exist_ok=True);text=json.dumps(cfg,indent=2)+'\n'
        if path.exists():assert path.read_text()==text,'Existing frozen stage plan changed'
        else:path.write_text(text)
        print(str(path.relative_to(ROOT)))
    inputs=list(lock['source_hashes'])+['runs/fresh-assembled/train-contexts.json','runs/fresh-assembled/validation-contexts.json','src/thresholds.py']
    plan('calibrate-primary.json','fit-probe','calibrate_fresh.py',[],inputs,['runs/fresh-calibration/lock.json']+['runs/fresh-calibration/'+n for n in lock['artifacts']],
         'Reproduce train-only grouped fitting and validation-only calibration in a clean replica with copied frozen inputs. Existing calibration deliberately refuses overwrite. Dry-run is safe in the current study; do not duplicate active work.')
    for dataset,stem,report in [('primary','fresh','final-comparison'),('template-challenge','template-challenge','template-challenge-comparison'),('specificity-controls','specificity-controls','specificity-controls-comparison')]:
        jd=ROOT/f'runs/{stem}-jview-test';mp=ROOT/f'runs/{stem}-assembled/manifest.json'
        if not (jd/'complete.json').exists() or not mp.exists():continue
        complete=json.loads((jd/'complete.json').read_text())
        if complete['errors']:continue
        assembled=json.loads(mp.read_text());inputs=list(lock['source_hashes'])+['runs/fresh-calibration/lock.json']+['runs/fresh-calibration/'+n for n in lock['artifacts']]+[str(mp.relative_to(ROOT))]+[f'runs/{stem}-assembled/'+n for n in assembled['files_sha256']]+[f'runs/{stem}-jview-test/scores.json',f'runs/{stem}-jview-test/complete.json','scripts/paired_breakdown.py','src/comparison_diagnostics.py']
        plan(f'compare-{dataset}.json','compare','evaluate_fresh.py',['--dataset',dataset],inputs,[f'reports/{report}/summary.json',f'reports/{report}/cases.json',f'reports/{report}/cases.csv'],
             'Recompute paired tables and uncertainty from frozen scores with the original primary calibration; no model training, new API calls or threshold selection.')

if __name__=='__main__':main()
