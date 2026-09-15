"""Freeze reproduction plans for completed secondary timing endpoints."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for offset in [32,64]:
        stem=f'fresh-offset{offset}';cal=ROOT/f'runs/{stem}-calibration';lockp=cal/'lock.json';lock=json.loads(lockp.read_text());data=ROOT/f'runs/{stem}-assembled';mp=data/'manifest.json';assembled=json.loads(mp.read_text());jd=ROOT/f'runs/{stem}-jview-test';complete=json.loads((jd/'complete.json').read_text())
        inputs=set(lock['source_hashes'])|{str(lockp.relative_to(ROOT)),str(mp.relative_to(ROOT)),'configs/identity-fp32.json','scripts/paired_breakdown.py','src/comparison_diagnostics.py'}
        inputs.update(str((cal/n).relative_to(ROOT)) for n in lock['artifacts']);inputs.update(str((data/n).relative_to(ROOT)) for n in assembled['files_sha256']);inputs.update(str((jd/n).relative_to(ROOT)) for n in ['scores.json','complete.json'])
        script='evaluate_fresh.py'
        if complete['errors']:
            assert offset==64
            from document_timing_refusals import validate_missing
            refusal=validate_missing(jd);script='evaluate_timing_with_missing.py';inputs.add('scripts/document_timing_refusals.py');inputs.add(str((jd/'documented-unavailable.json').relative_to(ROOT)))
            for row in refusal['unavailable']:inputs.update(str((jd/n).relative_to(ROOT)) for n in row['evidence'])
        inputs.add('scripts/'+script)
        cfg={'stage':'compare','identity_config':'configs/identity-fp32.json','inputs_sha256':{n:sha(ROOT/n) for n in sorted(inputs)},'commands':[{'script':script,'args':['--offset',str(offset)]}],'outputs':[f'reports/final-comparison-offset{offset}/{n}' for n in ['summary.json','cases.json','cases.csv']],'resource_estimate':{'gpu_hours':0,'api_calls':0,'basis':'CPU-only reconstruction from saved scores and explicit unavailable-judgment evidence'},'scope':'Reproduce separate endpoint calibration results; no retraining, API calls, threshold changes or relabeling. Provider refusals remain unavailable.'}
        p=ROOT/f'configs/stages/compare-offset{offset}.json';text=json.dumps(cfg,indent=2)+'\n'
        if p.exists():assert p.read_text()==text
        else:p.write_text(text)
        print(str(p.relative_to(ROOT)))
if __name__=='__main__':main()
