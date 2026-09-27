"""Fixed held-out review cohorts with exact cache reuse and eight concurrent calls."""
import argparse, importlib, json, math, shutil
from pathlib import Path
from audit_budgeted_reader import pause_budget
from budgeted_api_client import file_lock
from collect_local_readers import load_jobs, load_results, valid_score
from contracts import fingerprint
from finish_primary_with_missing import verify_result
from parallel_hosted_jobs import run_wave
from smoke import digest, write_json
from standard_temporal_reviews import load_acceptance

CANDIDATES={'gpt41reference':'reference','gpt54standardreference':'standardreference','gpt54lowreference':'lowreference'}

def verify_review(job,result,roots,c,s,ledger):
    if result.get('status')=='ok':return verify_result(job,result,roots,c,s,ledger)
    t=importlib.import_module('budgeted_hosted_'+s);request=t.payload(c,job['system'],job['evidence']);key=fingerprint(request)
    paths=[p for r in roots for p in (r/'api-cache').glob(key+'-raw-*.json')]
    if len(paths)!=1:raise ValueError('Expected unique unavailable receipt')
    raw=json.loads(paths[0].read_text());error=raw.get('response',{}).get('error')
    if error is None:return verify_result(job,result,roots,c,s,ledger)
    rec=ledger['records'][raw['budget_reservation']]
    manifest=importlib.import_module('hosted_text_reader_'+s).execution_manifest(c)
    if (raw['request']!=request or rec['request_sha256']!=key or rec['status']!='reserved'
        or error.get('code')!=502 or error.get('metadata',{}).get('error_type')!='provider_unavailable'
        or result!={'request_id':job['request_id'],'manifest_sha256':fingerprint(manifest),'status':'unavailable','error_type':'RuntimeError'}):
        raise ValueError('Undiagnosed unavailable response; preserve and investigate')
    return str(paths[0]),digest(paths[0])


def main():
    p=argparse.ArgumentParser()
    for n in ['budget-file','credential-file','out','plan-file']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    root=Path('runs/reader-comparison');hp=root/'heldout-review-handoff/complete.json'
    handoff=json.loads(hp.read_text());sources={str(hp):digest(hp)}
    unions={c:{} for c in CANDIDATES};cohorts={}
    for e,record in handoff['endpoints'].items():
        directory=Path(record['jobs']);m,jobs,aliases=load_jobs(directory)
        if digest(directory/'jobs.json')!=record['jobs_sha256'] or m['phase']!='test' or m['stage']!='reviews':raise ValueError('Fixed held-out cohort changed')
        if len(aliases)!=1152 or len({x['episode_id'] for x in aliases})!=128:raise ValueError('Expected full128 episodes and nine arms')
        prefix='standard' if e in ['during_action','after_action'] else 'accepted'
        lp=root/(prefix+'-calibration-'+e)/'lock.json';lock=json.loads(lp.read_text())
        for path,sha in lock['source_hashes'].items():
            if digest(path)!=sha:raise ValueError('Calibration source changed')
        if lock['identity']!=m['subject_identity'] or lock['endpoint']!=e:raise ValueError('Wrong lock')
        pair=['gpt41reference','gpt54standardreference' if prefix=='standard' else 'gpt54lowreference']
        cohorts[e]={'pair':pair,'jobs':str(directory),'lock':str(lp),'missing_aliases':sum(x['request_id'] is None for x in aliases)}
        for c in pair:
            for j in jobs:
                if j['request_id'] in unions[c] and unions[c][j['request_id']]!=j:raise ValueError('Request collision')
                unions[c][j['request_id']]=j
        for path in [lp,directory/'jobs.json',directory/'manifest.json',directory/'aliases.json']:sources[str(path)]=digest(path)
    ledger=json.loads(a.budget_file.read_text())
    if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=40:raise ValueError('Paused authorized40 required')
    attempted={r['request_sha256'] for r in ledger['records'].values()};pending={};cached={};costs={}
    for c,s in CANDIDATES.items():
        runner=importlib.import_module('hosted_text_reader_'+s);transport=importlib.import_module('budgeted_hosted_'+s)
        ap=Path('studies/reader_comparison/evidence')/('hosted-'+c+'-acceptance'+('-v2' if c=='gpt41reference' else '')+'.json')
        sources.update(load_acceptance(ap,runner.execution_manifest(c)))
        roots=sorted(p.parent for p in root.glob('*/'+c+'/manifest.json'))
        roots.append(root/('hosted-'+c+'-coverage')/'reader')
        jobs=sorted(unions[c].values(),key=lambda j:j['request_id']);found={}
        for prior in roots:
            manifest,results=load_results(prior,jobs)
            if manifest!=runner.execution_manifest(c):raise ValueError('Cached reader changed')
            for rid,x in results.items():
                if rid in found and found[rid][0]!=x:raise ValueError('Conflicting exact cache results')
                found[rid]=(x,prior/'results'/(rid+'.json'))
        pending[c]=[];cached[c]={}
        for j in jobs:
            key=fingerprint(transport.payload(c,j['system'],j['evidence']))
            if key in attempted:
                if j['request_id'] not in found:raise ValueError('Attempted request without reusable output; no retry')
                result,rp=found[j['request_id']];rawpath,sha=verify_review(j,result,roots,c,s,ledger)
                sources[str(rp)]=digest(rp);sources[rawpath]=sha;cached[c][j['request_id']]=str(rp)
            else:
                if j['request_id'] in found:raise ValueError('Unaccounted cache')
                pending[c].append(j)
        costs[c]={'cached':len(cached[c]),'new':len(pending[c]),'total':len(jobs),
                  'maximum_reservation_sum_microusd':sum(math.ceil(transport.reservation(c,transport.payload(c,j['system'],j['evidence']))*1e6) for j in pending[c])}
    plan={'cohorts':cohorts,'pending':pending,'cached_paths':cached,'source_hashes':sources,'costs':costs,
          'code_sha256':digest(__file__),'scheduler_sha256':digest(Path(__file__).with_name('parallel_hosted_jobs.py')),
          'scope':'Eight concurrent calls globally in fully budgeted waves, exact registered readers per endpoint. No Flex/standard score substitution. No retries/fallback or test-score aggregation. Preserve fixed locks and all missingness.'}
    if a.dry_run:
        if a.plan_file.exists():raise ValueError('Preserve registered plan')
        write_json(a.plan_file,plan);print(json.dumps(costs));return
    if json.loads(a.plan_file.read_text())!=plan:raise ValueError('Prepared plan changed')
    if a.out.exists():raise ValueError('Preserve prior output')
    a.out.mkdir(parents=True);write_json(a.out/'registration.json',plan)
    for c,s in CANDIDATES.items():
        (a.out/c/'results').mkdir(parents=True);(a.out/c/'api-cache').mkdir()
        write_json(a.out/c/'manifest.json',importlib.import_module('hosted_text_reader_'+s).execution_manifest(c))
        for rid,path in cached[c].items():shutil.copy2(path,a.out/c/'results'/(rid+'.json'))
    index=0;missing=[]
    try:
        while any(pending.values()):
            # Outcome-independent scheduling: service the largest remaining queue.
            c=max(pending,key=lambda c:len(pending[c]));s=CANDIDATES[c]
            runner=importlib.import_module('hosted_text_reader_'+s);t=importlib.import_module('budgeted_hosted_'+s)
            wave=pending[c][:8];requests=[t.payload(c,j['system'],j['evidence']) for j in wave]
            keys=[fingerprint(r) for r in requests];maximum=sum(math.ceil(t.reservation(c,r)*1e6) for r in requests)
            with file_lock(str(a.budget_file)+'.lock'):
                ledger=json.loads(a.budget_file.read_text());held=ledger['reserved_microusd']
                if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=40:raise ValueError('Concurrent coordinator or changed cap')
                if held!=sum(r['reserved_microusd'] for r in ledger['records'].values() if r['status']=='reserved'):raise ValueError('Reservation mismatch')
                if any(r['request_sha256'] in keys for r in ledger['records'].values()):raise ValueError('No retry')
                if maximum>40_000_000-held-ledger['spent_microusd']:raise ValueError('Whole wave exceeds available budget')
                ledger.update(status='active',active_request_allowlist=keys,active_audit_manifest_sha256=digest(a.plan_file))
                write_json(a.budget_file,ledger)
            try:completed=run_wave(c,wave,runner.run_jobs,a.out/f'wave-{index}',a.credential_file,a.budget_file)
            finally:ledger=pause_budget(a.budget_file)
            wave_missing=0
            for j,reader in completed:
                rp=reader/'results'/(j['request_id']+'.json');result=json.loads(rp.read_text())
                rawpath,sha=verify_review(j,result,[reader],c,s,ledger);sources[rawpath]=sha;sources[str(rp)]=digest(rp)
                if valid_score(result) is None:missing.append({'candidate':c,'request_id':j['request_id']});wave_missing+=1
                for sub in ['results','api-cache']:
                    for path in (reader/sub).glob('*.json'):
                        target=a.out/c/sub/path.name
                        if target.exists():raise ValueError('Refuse overwrite')
                        shutil.copy2(path,target)
            pending[c]=pending[c][len(wave):];index+=1
            if wave_missing>=3:raise ValueError('Unavailable cluster; completed wave drained, stop dispatch')
            write_json(a.out/'progress.json',{'remaining':{c:len(v) for c,v in pending.items()},'missing':missing,'completed_waves':index})
        write_json(a.out/'complete.json',{'cohorts':cohorts,'costs':costs,'missing':missing,'source_hashes':sources})
    finally:
        ledger=pause_budget(a.budget_file);write_json(a.out/'cost.json',{k:ledger.get(k) for k in ['status','spent_microusd','reserved_microusd','additional_limit_usd']})

if __name__=='__main__':main()
