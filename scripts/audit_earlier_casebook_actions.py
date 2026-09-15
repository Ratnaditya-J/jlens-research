"""Re-execute prespecified held-out casebook cases and align external action evidence."""
import argparse, fcntl, hashlib, json, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');p.add_argument('--offset',type=int,choices=[32,64],required=True);a=p.parse_args()
    folder=ROOT/'runs/controller';folder.mkdir(parents=True,exist_ok=True)
    lock=(folder/f'casebook-action-audit-offset{a.offset}.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    marker=folder/'fresh-scoring-complete.json'
    if a.wait:
        while not marker.exists():time.sleep(60)
    assert marker.exists()
    reportdir=ROOT/f'reports/final-comparison-offset{a.offset}';sp=reportdir/'summary.json';summary=json.loads(sp.read_text())
    cfg=json.loads((ROOT/'configs/fresh-v1.json').read_text());indices={e['episode_id']:i for i,e in enumerate(cfg['episodes'])}
    cases={r['episode_id']:r for r in json.loads((reportdir/'cases.json').read_text())}
    output=ROOT/f'runs/action-traces-final-offset{a.offset}';output.mkdir(parents=True,exist_ok=True);rows=[]
    for eid in summary['casebook_ids']:
        ep=ROOT/'runs/fresh'/eid/'episode.json';audit=ep.with_name('external-audit.json');baseline=json.loads(audit.read_text())
        row={'episode_id':eid,'category':cases[eid]['category'],'behavior_label':cases[eid]['behavior_label'],'episode_sha256':sha(ep),'baseline_sha256':sha(audit)}
        if baseline['status']!='executed':
            rows.append({**row,'unavailable':'original audit not executed'});continue
        tracepath=output/(eid+'.json')
        subprocess.run(['/workspace/work/wasm-venv/bin/python',str(ROOT/'scripts/action_trace.py'),str(ep),'--output',str(tracepath)],check=True,timeout=30)
        trace=json.loads(tracepath.read_text());row.update(trace_sha256=sha(tracepath),observables_match_original_audit=trace['observables_match_original_audit'])
        d=ROOT/f'runs/fresh-processed-{indices[eid]%4}'/eid;complete=json.loads((d/'complete.json').read_text())
        for name in ['source-lines.json','positions.json']:
            assert sha(d/name)==complete['files_sha256'][name]
        mapping=json.loads((d/'source-lines.json').read_text());pos=json.loads((d/'positions.json').read_text())
        assert mapping['episode_sha256']==row['episode_sha256']
        if mapping.get('code_sha256') is not None:assert mapping['code_sha256']==baseline['code_sha256']
        row.update(source_lines_sha256=sha(d/'source-lines.json'),positions_sha256=sha(d/'positions.json'))
        byline={r['source_line']:r for r in mapping['lines']};lines=trace['candidate_executed_source_lines']
        if not trace['observables_match_original_audit'] or not lines or 'unavailable' in mapping or any(line not in byline for line in lines):
            rows.append({**row,'unavailable':'No supported, behavior-preserving action localization'});continue
        boundary=min(byline[line]['before_statement_sample_index'] for line in lines)
        onset=pos['positions'][str(a.offset)]['sample_index'];assert boundary>=onset
        row.update(candidate_source_lines=lines,localized_statement_sample_index=boundary,scored_sample_index=onset,scored_offset_before_code_onset=a.offset,token_gap=boundary-onset)
        for detector in ['probe','jlens']:
            row[detector+'_flag_at_scored_position']=cases[eid][detector+'_flag']
            row[detector+'_flag_lead_tokens']=boundary-onset if cases[eid][detector+'_flag'] else None
        rows.append(row)
    result={'selection':'Unchanged category-by-label, up to three lowest-SHA episode IDs from primary held-out evaluation','summary_sha256':sha(sp),'script_sha256':sha(Path(__file__)),'rows':rows,'limitations':['Does not relabel cases or alter frozen detector flags','Guest tracing can be tampered with and supports only selected mechanisms','Token gaps from one scored endpoint are not earliest detection times or deployment latency','Selected casebook cases do not estimate population rates']}
    dest=reportdir/'action-audit.json';dest.write_text(json.dumps(result,indent=2)+'\n')
    (folder/f'casebook-action-audit-offset{a.offset}-complete.json').write_text(json.dumps({'report_sha256':sha(dest),'cases':len(rows)})+'\n')

if __name__=='__main__':main()
