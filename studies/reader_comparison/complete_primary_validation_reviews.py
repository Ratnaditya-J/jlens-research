"""Finish the fixed primary validation review cohort in fully reserved small batches."""
import argparse
import importlib
import json
import math
import shutil
from pathlib import Path
from accepted_review_tranche import CANDIDATES, JOBS_SHA
from audit_budgeted_reader import pause_budget
from budgeted_api_client import file_lock
from collect_local_readers import load_jobs, load_results, valid_score
from contracts import fingerprint
from smoke import digest, write_json
from verify_accepted_review_receipts import audit
from verify_reader_acceptance import load_acceptance

KIND='accepted-primary-validation-remaining188-v1'


def activate(path, plan):
    keys=plan['request_allowlist']
    if plan.get('kind')!=KIND or plan.get('jobs_sha256')!=JOBS_SHA or not 1<=len(keys)<=32 or len(set(keys))!=len(keys):
        raise ValueError('Unregistered validation batch')
    with file_lock(str(path)+'.lock'):
        ledger=json.loads(path.read_text());held=ledger.get('reserved_microusd',0)
        if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=5:raise ValueError('Existing paused$5 allowance required')
        if held!=sum(r['reserved_microusd'] for r in ledger['records'].values() if r['status']=='reserved'):raise ValueError('Unknown accounting changed')
        if any(r['request_sha256'] in keys for r in ledger['records'].values()):raise ValueError('No retries')
        if not 0<plan['maximum_reserved_microusd']<=5_000_000-held-ledger.get('spent_microusd',0):raise ValueError('Batch unaffordable; do not raise cap')
        ledger.update(status='active',active_request_allowlist=keys,active_audit_manifest_sha256=fingerprint(plan),audit_scope=plan['scope'])
        write_json(path,ledger)


def main():
    p=argparse.ArgumentParser()
    for name in ['jobs','prior','budget-file','credential-file','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();m,jobs,_=load_jobs(a.jobs)
    if m['phase']!='validation' or m['stage']!='reviews' or m['endpoint']!='before_action' or digest(a.jobs/'jobs.json')!=JOBS_SHA:raise ValueError('Wrong cohort')
    ledger=json.loads(a.budget_file.read_text())
    if not ledger['status'].startswith('paused'):raise ValueError('Prior coordinator must terminate first')
    prior_cost=json.loads((a.prior/'cost.json').read_text())
    if not prior_cost['status'].startswith('paused'):raise ValueError('Prior tranche incomplete')
    prior_plan=json.loads((a.prior/'plan.json').read_text())
    if prior_plan['kind']!='accepted-primary-validation-review-first64-v1' or prior_plan['jobs_sha256']!=JOBS_SHA:raise ValueError('Wrong predecessor')
    pending={};sources={};initial={}
    for candidate,suffix in CANDIDATES:
        runner=importlib.import_module('hosted_text_reader_'+suffix)
        acceptance=Path('studies/reader_comparison/evidence')/('hosted-'+candidate+'-acceptance'+('-v2' if suffix=='reference' else '')+'.json')
        sources.update(load_acceptance(acceptance,runner.execution_manifest(candidate)))
        report=audit(a.prior/(candidate+'-jobs.json'),a.prior/candidate,a.budget_file,candidate,suffix)
        if report['verified_reviews']!=32:raise ValueError('Prior tranche size changed')
        sources.update(report['source_hashes']);manifest,results=load_results(a.prior/candidate,jobs)
        if manifest!=runner.execution_manifest(candidate) or len(results)!=50:raise ValueError('Expected50 prior results')
        for source in prior_plan['reused_results'][candidate]:
            source=Path(source)
            if sources.get(str(source.resolve()))!=digest(source) or digest(a.prior/candidate/'results'/source.name)!=digest(source):raise ValueError('Cached result changed')
        if any(valid_score(r) is None for r in results.values()):raise ValueError('Prior invalid result')
        initial[candidate]=results
        pending[candidate]=[j for j in sorted(jobs,key=lambda j:j['request_id']) if j['request_id'] not in results]
        if len(pending[candidate])!=94:raise ValueError('Wrong remaining cohort')
    if a.out.exists():raise ValueError('Preserve previous execution; no automatic restart')
    a.out.mkdir(parents=True)
    write_json(a.out/'registration.json',{'kind':KIND,'jobs_sha256':JOBS_SHA,'pending':pending,'source_hashes':sources,'code_sha256':digest(__file__),'scope':'Remaining94 fixed primary validation reviews per judge, in batches of at most16 per judge. Each complete batch reservation must fit existing$5 ledger after uncertain charges. No retries, fallback, budget increase, calibration lock or held-out inference.'})
    for candidate,suffix in CANDIDATES:
        root=a.out/candidate;root.mkdir();(root/'results').mkdir()
        shutil.copyfile(a.prior/candidate/'manifest.json',root/'manifest.json')
        for rid,result in initial[candidate].items():write_json(root/'results'/(rid+'.json'),result)
    for index,start in enumerate(range(0,94,16)):
        selected={c:pending[c][start:start+16] for c,_ in CANDIDATES};keys=[];maximum=0
        for candidate,suffix in CANDIDATES:
            transport=importlib.import_module('budgeted_hosted_'+suffix)
            for job in selected[candidate]:
                request=transport.payload(candidate,job['system'],job['evidence']);keys.append(fingerprint(request));maximum+=math.ceil(transport.reservation(candidate,request)*1e6)
        plan={'kind':KIND,'jobs_sha256':JOBS_SHA,'index':index,'request_allowlist':keys,'maximum_reserved_microusd':maximum,'scope':'Fully reserved bounded primary validation batch; no retries/cap increase/held-out scoring.'}
        write_json(a.out/('batch-'+str(index)+'-plan.json'),plan)
        activate(a.budget_file,plan)
        try:
            for candidate,suffix in CANDIDATES:
                if json.loads(a.budget_file.read_text())['status']!='active':raise RuntimeError('Budget/provider pause; stop coordinator')
                path=a.out/(candidate+'-batch-'+str(index)+'-jobs.json');write_json(path,{'jobs':selected[candidate]})
                importlib.import_module('hosted_text_reader_'+suffix).run_jobs(candidate,path,a.out/candidate,a.credential_file,a.budget_file)
                report=audit(path,a.out/candidate,a.budget_file,candidate,suffix)
                write_json(a.out/(candidate+'-batch-'+str(index)+'-receipts.json'),report)
        finally:
            ledger=pause_budget(a.budget_file)
            write_json(a.out/('batch-'+str(index)+'-cost.json'),{k:ledger.get(k) for k in ['status','spent_microusd','reserved_microusd']})
    for candidate,_ in CANDIDATES:
        _,results=load_results(a.out/candidate,jobs)
        if len(results)!=144 or any(valid_score(r) is None for r in results.values()):raise ValueError('Incomplete final cohort')
    write_json(a.out/'complete.json',{'jobs_sha256':JOBS_SHA,'reviews_per_judge':144,'scope':'Primary validation reviews complete. Calibration and held-out evaluation remain separate.'})


if __name__=='__main__':main()
