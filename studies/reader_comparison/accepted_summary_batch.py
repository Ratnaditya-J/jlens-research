"""One registered64-request primary validation-summary batch after acceptance."""
import argparse
import json
import math
import shutil
from pathlib import Path
from audit_budgeted_reader import pause_budget
from budgeted_api_client import file_lock
from budgeted_hosted_lowreference import payload,reservation
from collect_local_readers import load_jobs
from contracts import fingerprint
from hosted_text_reader_lowreference import execution_manifest,run_jobs
from hosted_text_reader_reference import execution_manifest as first_manifest
from smoke import digest,write_json
from verify_reader_acceptance import load_acceptance

JOBS_SHA='b4706d4df8a6c30811785a9c32457732b1eda86d26e982e095fbfab3d1de89c0'
KIND='accepted-primary-validation-summary64-v1'


def activate(path,plan):
    if plan.get('kind')!=KIND or plan.get('jobs_sha256')!=JOBS_SHA:raise ValueError('Unregistered summary cohort')
    keys=plan['request_allowlist']
    if len(keys)!=64 or len(set(keys))!=64:raise ValueError('Exactly64 summary requests required')
    with file_lock(str(path)+'.lock'):
        ledger=json.loads(path.read_text())
        if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=5:raise ValueError('Paused existing$5 allocation required')
        held=ledger.get('reserved_microusd',0)
        if held!=sum(r['reserved_microusd'] for r in ledger['records'].values() if r['status']=='reserved'):raise ValueError('Uncertain accounting differs')
        if any(r['request_sha256'] in keys for r in ledger['records'].values()):raise ValueError('Request already attempted; no retry')
        if plan['maximum_reserved_microusd']>5_000_000-ledger.get('spent_microusd',0)-held:raise ValueError('Entire batch must fit existing allowance')
        ledger.update(status='active',active_request_allowlist=keys,active_audit_manifest_sha256=fingerprint(plan),audit_scope=plan['scope'],carried_uncertain_microusd_at_activation=held)
        write_json(path,ledger)


def main():
    p=argparse.ArgumentParser()
    for name in ['jobs','first-acceptance','summary-acceptance','credential-file','budget-file','out']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    m,jobs,_=load_jobs(a.jobs)
    if m['phase']!='validation' or m['stage']!='summaries' or m['endpoint']!='before_action' or digest(a.jobs/'jobs.json')!=JOBS_SHA:
        raise ValueError('Only frozen primary validation-summary cohort allowed')
    expected=execution_manifest('gpt54lowreference')
    sources=load_acceptance(a.first_acceptance,first_manifest('gpt41reference'))
    sources.update(load_acceptance(a.summary_acceptance,expected))
    requests=[payload('gpt54lowreference',j['system'],j['evidence']) for j in jobs]
    plan={'kind':KIND,'jobs_sha256':JOBS_SHA,'input_manifest_sha256':digest(a.jobs/'manifest.json'),
          'reader_manifest':expected,'acceptance_source_hashes':sources,
          'request_allowlist':sorted(fingerprint(r) for r in requests),
          'maximum_reserved_microusd':sum(math.ceil(reservation('gpt54lowreference',r)*1e6) for r in requests),
          'code_sha256':digest(__file__),
          'scope':'64 unique pre-action validation token-only summaries. No task context or outcome labels sent. Staged execution of the full comparison, not a reduction of endpoints or controls. No retries, held-out inference or cap increase. Unused reservations release only on known settlement.'}
    if a.dry_run:print(json.dumps(plan,indent=2));return
    if a.out.exists():raise ValueError('Preserve prior batch; no automatic restart')
    a.out.mkdir(parents=True);write_json(a.out/'plan.json',plan)
    jobs_path=a.out/'primary-validation-summary-jobs.json';shutil.copyfile(a.jobs/'jobs.json',jobs_path)
    activate(a.budget_file,plan)
    try:run_jobs('gpt54lowreference',jobs_path,a.out/'reader',a.credential_file,a.budget_file)
    finally:
        ledger=pause_budget(a.budget_file)
        write_json(a.out/'cost.json',{'spent_microusd':ledger.get('spent_microusd',0),'reserved_microusd':ledger.get('reserved_microusd',0),'status':ledger['status'],'ledger_sha256':digest(a.budget_file)})


if __name__=='__main__':main()
