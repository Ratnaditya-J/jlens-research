"""Fixed during/after-action validation summaries with adaptive fully reserved batches."""
import argparse,json,math
from pathlib import Path
from audit_budgeted_reader import pause_budget
from budgeted_api_client import file_lock
from budgeted_hosted_lowreference import payload,reservation
from collect_local_readers import load_jobs
from contracts import fingerprint
from hosted_text_reader_lowreference import execution_manifest,run_jobs
from smoke import digest,write_json
from verify_reader_acceptance import load_acceptance
from verify_accepted_summary_receipts import audit

HASHES={'during_action':'b05a25e04c42bbea2686f82e13402ae2632b24b679d2a7aa2774e57219e97d13','after_action':'5e223e7e311efba5a1b5fc27135b1453728a1330d3ebce6ca9264fa0063dea05'}


def main():
 p=argparse.ArgumentParser()
 for n in ['budget-file','credential-file','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();root=Path('runs/reader-comparison')
 # Accounted-for requests can include observed, settled truncations; never retry them.
 primary=root/'accepted-early-validation-reviews/complete.json'
 complete=json.loads(primary.read_text())
 if set(complete['coverage'])!={'gpt41reference','gpt54lowreference'} or any(v['attempted']!=288 for v in complete['coverage'].values()):raise ValueError('Earlier validation reviews must be fully accounted for')
 for path,sha in complete['source_hashes'].items():
  if digest(path)!=sha:raise ValueError('Earlier validation receipt provenance changed')
 sources=load_acceptance(Path('studies/reader_comparison/evidence/hosted-gpt54lowreference-acceptance.json'),execution_manifest('gpt54lowreference'))
 sources[str(primary)]=digest(primary)
 union={}
 for endpoint,sha in HASHES.items():
  path=root/('local-summary-validation-'+endpoint);m,jobs,_=load_jobs(path)
  if m['phase']!='validation' or m['stage']!='summaries' or m['endpoint']!=endpoint or digest(path/'jobs.json')!=sha:raise ValueError('Wrong cohort')
  for job in jobs:
   if job['request_id'] in union and union[job['request_id']]!=job:raise ValueError('Request collision')
   union[job['request_id']]=job
  for name in ['jobs.json','manifest.json','aliases.json']:sources[str(path/name)]=digest(path/name)
 jobs=sorted(union.values(),key=lambda j:j['request_id'])
 if len(jobs)!=428:raise ValueError('Expected428 summaries')
 if a.out.exists():raise ValueError('Preserve prior batch, no restart')
 a.out.mkdir(parents=True)
 write_json(a.out/'registration.json',{'cohorts':HASHES,'source_hashes':sources,'code_sha256':digest(__file__),'scope':'428 during/after-action validation summaries in content-hash-ordered fully reserved batches of at most32. Same accepted execution. No reviews, retries, fallback, cap increase or held-out access.'})
 index=0;pending=jobs
 while pending:
  ledger=json.loads(a.budget_file.read_text());available=7_000_000-ledger.get('spent_microusd',0)-ledger.get('reserved_microusd',0)
  for size in range(min(32,len(pending)),0,-1):
   batch=pending[:size];requests=[payload('gpt54lowreference',j['system'],j['evidence']) for j in batch];keys=[fingerprint(r) for r in requests];maximum=sum(math.ceil(reservation('gpt54lowreference',r)*1e6) for r in requests)
   if maximum<=available:break
  else:raise ValueError('Minimum summary reservation unaffordable; no cap increase')
  plan={'index':index,'request_allowlist':keys,'maximum_reserved_microusd':maximum,'cohorts':HASHES};write_json(a.out/f'batch-{index}-plan.json',plan)
  with file_lock(str(a.budget_file)+'.lock'):
   ledger=json.loads(a.budget_file.read_text());held=ledger.get('reserved_microusd',0)
   if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=7:raise ValueError('Paused registered$7 allocation required')
   if held!=sum(r['reserved_microusd'] for r in ledger['records'].values() if r['status']=='reserved'):raise ValueError('Unknown accounting changed')
   if any(r['request_sha256'] in keys for r in ledger['records'].values()):raise ValueError('No retries')
   if maximum>7_000_000-ledger.get('spent_microusd',0)-held:raise ValueError('Whole batch must fit existing allowance')
   ledger.update(status='active',active_request_allowlist=keys,active_audit_manifest_sha256=fingerprint(plan),audit_scope='Registered during/after-action validation summaries only');write_json(a.budget_file,ledger)
  try:
   path=a.out/f'batch-{index}-jobs.json';write_json(path,{'jobs':batch});run_jobs('gpt54lowreference',path,a.out/'reader',a.credential_file,a.budget_file)
   receipt=audit(path,a.out/'reader',a.budget_file,'gpt54lowreference','lowreference');write_json(a.out/f'batch-{index}-receipts.json',receipt);sources.update(receipt['source_hashes'])
  finally:
   ledger=pause_budget(a.budget_file);write_json(a.out/f'batch-{index}-cost.json',{k:ledger.get(k) for k in ['status','spent_microusd','reserved_microusd']})
  pending=pending[len(batch):];index+=1
 write_json(a.out/'complete.json',{'unique_summaries':428,'cohorts':HASHES,'source_hashes':sources,'scope':'Schema-valid validation summaries with verified raw responses and settlement receipts. Semantic fidelity not established.'})


if __name__=='__main__':main()
