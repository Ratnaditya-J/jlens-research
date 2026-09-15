"""Temporal transfer of frozen code-onset detectors, without endpoint retuning."""
import argparse, fcntl, hashlib, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from paired_breakdown import summarize
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def sampled_earliest(rows,field):
    available=[r for r in rows if r.get(field) is not None]
    flagged=[r['offset_before_code_onset'] for r in available if r[field]]
    return {'earliest_flagged_sample_offset':max(flagged) if flagged else None,
            'available_offsets':sorted([r['offset_before_code_onset'] for r in available],reverse=True),
            'missing_offsets':sorted([r['offset_before_code_onset'] for r in rows if r.get(field) is None],reverse=True)}

def main():
    import numpy as np,joblib
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');a=p.parse_args()
    folder=ROOT/'runs/controller';folder.mkdir(parents=True,exist_ok=True)
    guard=(folder/'timing-transfer.lock').open('a');fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
    marker=folder/'earlier-position-scoring-complete.json'
    if a.wait:
        while not marker.exists():time.sleep(60)
    assert marker.exists()
    cal=ROOT/'runs/fresh-calibration';lockp=cal/'lock.json';lock=json.loads(lockp.read_text());sources={str(lockp.relative_to(ROOT)):sha(lockp)}
    for name,digest in lock['source_hashes'].items():assert sha(ROOT/name)==digest
    for name,digest in lock['artifacts'].items():assert sha(cal/name)==digest
    model=joblib.load(cal/'probe.joblib');allrows=[];tables={}
    for offset in [0,32,64]:
        stem='fresh'+(f'-offset{offset}' if offset else '');data=ROOT/f'runs/{stem}-assembled';mp=data/'manifest.json';manifest=json.loads(mp.read_text())
        for name,digest in manifest['files_sha256'].items():assert sha(data/name)==digest
        sources[str(mp.relative_to(ROOT))]=sha(mp)
        records=json.loads((data/'test-records.json').read_text());features=np.load(data/'test-features.npz');x=features[f"layer_{lock['selected']['layer']}"]
        scores=model.predict_proba(x.astype(np.float64))[:,1] if len(x) else []
        jd=ROOT/f'runs/{stem}-jview-test';jlookup={}
        if (jd/'complete.json').exists():
            complete=json.loads((jd/'complete.json').read_text());assert not complete['errors'];assert sha(jd/'scores.json')==complete['scores_sha256']
            sources[str((jd/'scores.json').relative_to(ROOT))]=sha(jd/'scores.json');jlookup={r['episode_id']:r['jview']['score'] for r in json.loads((jd/'scores.json').read_text())}
        cases=[]
        for r in records:
            i=r['feature_index'];cases.append({'episode_id':r['episode_id'],'task_group':r['family_id'],'behavior_label':r['label'] if r['label'] in ['misaligned','benign','uncertain'] else 'unavailable','probe_score':float(scores[i]) if i is not None else None,'jlens_score':jlookup.get(r['episode_id'])})
        protocol={'split':'test','threshold_source':'validation','observation_boundary':f'{offset}_tokens_before_code_onset','probe_threshold':lock['probe_threshold'],'jlens_threshold':lock['jview_threshold']}
        table,joined=summarize({'protocol':protocol,'cases':cases});tables[str(offset)]=table
        # Preserve individual availability even where the paired comparison excludes a case.
        for row in joined:
            row['offset_before_code_onset']=offset
            row['probe_flag']=row['probe_score']>=lock['probe_threshold'] if row['probe_score'] is not None else None
            row['jlens_flag']=row['jlens_score']>=lock['jview_threshold'] if row['jlens_score'] is not None else None
        allrows.extend(joined)
    episodes={}
    for row in allrows:episodes.setdefault(row['episode_id'],[]).append(row)
    temporal=[{'episode_id':eid,'probe':sampled_earliest(rows,'probe_flag'),'jlens':sampled_earliest(rows,'jlens_flag')} for eid,rows in episodes.items()]
    out=ROOT/'reports/timing-transfer';out.mkdir(parents=True,exist_ok=True)
    report={'scope':'Fixed primary code-onset probe weights and primary J-view threshold applied at all available earlier positions; secondary descriptive temporal transfer','source_sha256':sources,'script_sha256':sha(Path(__file__)),'tables_by_offset':tables,'sampled_detection':temporal,'limitations':['No retraining or threshold selection on earlier test scores','Validation FPR at code onset is not a guarantee of FPR at earlier positions','Only offsets0/32/64: earliest flagged sample is not the actual first detection time','Missing or unsupported J interpretation is not a negative flag','Different available-case populations across offsets can confound aggregate comparisons; paired trajectories preserve availability','Token offset is not wall-clock intervention lead or a measurement of mental commitment']}
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(out/'cases.json').write_text(json.dumps(allrows,indent=2)+'\n')
    (folder/'timing-transfer-complete.json').write_text(json.dumps({'summary_sha256':sha(out/'summary.json'),'cases_sha256':sha(out/'cases.json')})+'\n')

if __name__=='__main__':main()
