"""Resume unattempted held-out summaries, retaining diagnosed provider missingness."""
import argparse
import json
import math
import shutil
from pathlib import Path
from audit_budgeted_reader import pause_budget
from budgeted_api_client import file_lock
from budgeted_hosted_lowreference import payload, reservation
from hosted_text_reader_lowreference import execution_manifest, run_jobs
from contracts import fingerprint
from smoke import digest, write_json
from verify_accepted_summary_receipts import verify_one
from parallel_hosted_jobs import run_wave

CANDIDATE = 'gpt54lowreference'

def verify(job, reader, ledger):
    rp=reader/'results'/(job['request_id']+'.json')
    result=json.loads(rp.read_text())
    request=payload(CANDIDATE,job['system'],job['evidence']);key=fingerprint(request)
    paths=list((reader/'api-cache').glob(key+'-raw-*.json'))
    if len(paths)!=1:raise ValueError('Expected unique raw response; never retry')
    raw=json.loads(paths[0].read_text());record=ledger['records'][raw['budget_reservation']]
    if result.get('status')=='ok':
        verify_one(job,result,raw,record,CANDIDATE,'lowreference')
        missing=None
    else:
        error=raw.get('response',{}).get('error',{})
        if (raw['request']!=request or record['request_sha256']!=key or record['status']!='reserved'
            or error.get('code')!=502 or error.get('metadata',{}).get('error_type')!='provider_unavailable'
            or result!={'request_id':job['request_id'],'manifest_sha256':fingerprint(execution_manifest(CANDIDATE)),
                        'status':'unavailable','error_type':'RuntimeError'}):
            raise ValueError('Undiagnosed failure; preserve and stop')
        missing={'request_id':job['request_id'],'request_sha256':key,'reservation':raw['budget_reservation'],
                 'reserved_microusd':record['reserved_microusd'],'reason':'provider_unavailable_502'}
    return missing,{str(p):digest(p) for p in [rp,paths[0]]}

def main():
    p=argparse.ArgumentParser()
    for n in ['prior','out','budget-file','credential-file']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();pp=Path('studies/reader_comparison/evidence/heldout-summary-union-preflight.json')
    preflight=json.loads(pp.read_text());jobs=preflight['jobs'];sources={str(pp):digest(pp)}
    if len(jobs)!=588:raise ValueError('Fixed588 held-out summary requests required')
    for path,sha in preflight['source_hashes'].items():
        if digest(path)!=sha:raise ValueError('Prepared input changed')
        sources[path]=sha
    for e in ['during_action','after_action','before_action_32','before_action_64']:
        prefix='standard' if e in ['during_action','after_action'] else 'accepted'
        lp=Path('runs/reader-comparison')/(prefix+'-calibration-'+e)/'lock.json'
        lock=json.loads(lp.read_text());sources[str(lp)]=digest(lp)
        for path,sha in lock['source_hashes'].items():
            if digest(path)!=sha:raise ValueError('Frozen calibration source changed')
    ledger=json.loads(a.budget_file.read_text())
    if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=40:
        raise ValueError('Paused authorized40 allocation required')
    if json.loads((a.prior/'reader/manifest.json').read_text())!=execution_manifest(CANDIDATE):
        raise ValueError('Preserved summary execution changed')
    attempted={r['request_sha256'] for r in ledger['records'].values()}
    pending=[];missing=[]
    for j in jobs:
        key=fingerprint(payload(CANDIDATE,j['system'],j['evidence']))
        if key in attempted:
            item,hashes=verify(j,a.prior/'reader',ledger);sources.update(hashes)
            if item:missing.append(item)
        else:
            if (a.prior/'reader/results'/(j['request_id']+'.json')).exists():raise ValueError('Unaccounted cache')
            pending.append(j)
    if a.out.exists():raise ValueError('Preserve prior outputs')
    a.out.mkdir(parents=True);shutil.copytree(a.prior/'reader',a.out/'reader')
    write_json(a.out/'registration.json',{'pending_ids':[j['request_id'] for j in pending],
        'preserved_missing':missing,'source_hashes':sources,'code_sha256':digest(__file__),
        'orchestration':{'workers':8,'wave_size':8,'scope':'Concurrency across unchanged singleton reader invocations; same payloads and decoding. No new scientific protocol or reader-model change.'},'scope':'Same588 summary union; preserve prior successes and missingness. No retries/fallback. Fully reserve each bounded wave against shared ledger. Drain in-flight requests before pause. Stop after three provider failures in a wave or any undiagnosed failure.'})
    try:
        for start in range(0,len(pending),8):
            wave=pending[start:start+8]
            requests=[payload(CANDIDATE,j['system'],j['evidence']) for j in wave]
            keys=[fingerprint(r) for r in requests]
            maximum=sum(math.ceil(reservation(CANDIDATE,r)*1e6) for r in requests)
            with file_lock(str(a.budget_file)+'.lock'):
                ledger=json.loads(a.budget_file.read_text());held=ledger['reserved_microusd']
                if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=40:raise ValueError('Unexpected active coordinator or cap')
                if held!=sum(r['reserved_microusd'] for r in ledger['records'].values() if r['status']=='reserved'):raise ValueError('Reservation mismatch')
                if any(r['request_sha256'] in keys for r in ledger['records'].values()):raise ValueError('No retry')
                if maximum>40_000_000-held-ledger['spent_microusd']:raise ValueError('Whole wave must fit authorized funds')
                ledger.update(status='active',active_request_allowlist=keys,active_audit_manifest_sha256=digest(a.out/'registration.json'))
                write_json(a.budget_file,ledger)
            try:completed=run_wave(CANDIDATE,wave,run_jobs,a.out/f'wave-{start//8}',a.credential_file,a.budget_file)
            finally:ledger=pause_budget(a.budget_file)
            failed=0
            for j,reader in completed:
                item,hashes=verify(j,reader,ledger);sources.update(hashes)
                for sub in ['results','api-cache']:
                    for path in (reader/sub).glob('*.json'):
                        dest=a.out/'reader'/sub/path.name
                        if dest.exists():raise ValueError('Refuse to replace a prior response')
                        shutil.copy2(path,dest)
                if item:missing.append(item);failed+=1
            write_json(a.out/'progress.json',{'new_accounted':start+len(wave),'missing':missing,'remaining':len(pending)-start-len(wave),'workers':8})
            if failed>=3:raise ValueError('Provider outage cluster; wave drained, no further dispatch')
        write_json(a.out/'complete.json',{'requests':588,'usable':588-len(missing),'missing':missing,'source_hashes':sources})
    finally:
        ledger=pause_budget(a.budget_file)
        write_json(a.out/'cost.json',{k:ledger.get(k) for k in ['status','spent_microusd','reserved_microusd','additional_limit_usd']})

if __name__=='__main__':main()
