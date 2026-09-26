"""Fixed earlier-token validation controls, four bounded batches, no held-out data."""
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

HASHES={'before_action_32':'6512f1d50851f00b55a132192d0f9d232ffe4dca1518ff45c9210af862aff9e3','before_action_64':'8a1917cdefe3e2a538730413337c1aa13515cfbfe3929774fba2eaf3067e31f0'}


def main():
 p=argparse.ArgumentParser()
 for n in ['budget-file','credential-file','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();root=Path('runs/reader-comparison')
 # A completion record is written only after every primary review was verified.
 if not (root/'accepted-primary-validation-reviews-remaining188/complete.json').exists():raise ValueError('Primary reviews must finish first')
 sources=load_acceptance(Path('studies/reader_comparison/evidence/hosted-gpt54lowreference-acceptance.json'),execution_manifest('gpt54lowreference'))
 union={}
 for endpoint,sha in HASHES.items():
  path=root/('local-summary-validation-'+endpoint);m,jobs,_=load_jobs(path)
  if m['phase']!='validation' or m['stage']!='summaries' or m['endpoint']!=endpoint or digest(path/'jobs.json')!=sha:raise ValueError('Wrong cohort')
  for job in jobs:
   if job['request_id'] in union and union[job['request_id']]!=job:raise ValueError('Request collision')
   union[job['request_id']]=job
  for name in ['jobs.json','manifest.json','aliases.json']:sources[str(path/name)]=digest(path/name)
 jobs=sorted(union.values(),key=lambda j:j['request_id'])
 if len(jobs)!=128:raise ValueError('Expected128 controls')
 if a.out.exists():raise ValueError('Preserve prior batch, no restart')
 a.out.mkdir(parents=True)
 write_json(a.out/'registration.json',{'cohorts':HASHES,'source_hashes':sources,'code_sha256':digest(__file__),'scope':'128 earlier-token validation summaries in four32-request fully reserved batches. Same accepted execution. No reviews, retries, fallback, cap increase or held-out access.'})
 for index in range(4):
  batch=jobs[index*32:(index+1)*32];requests=[payload('gpt54lowreference',j['system'],j['evidence']) for j in batch];keys=[fingerprint(r) for r in requests];maximum=sum(math.ceil(reservation('gpt54lowreference',r)*1e6) for r in requests)
  plan={'index':index,'request_allowlist':keys,'maximum_reserved_microusd':maximum,'cohorts':HASHES};write_json(a.out/f'batch-{index}-plan.json',plan)
  with file_lock(str(a.budget_file)+'.lock'):
   ledger=json.loads(a.budget_file.read_text());held=ledger.get('reserved_microusd',0)
   if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=5:raise ValueError('Paused existing$5 allocation required')
   if held!=sum(r['reserved_microusd'] for r in ledger['records'].values() if r['status']=='reserved'):raise ValueError('Unknown accounting changed')
   if any(r['request_sha256'] in keys for r in ledger['records'].values()):raise ValueError('No retries')
   if maximum>5_000_000-ledger.get('spent_microusd',0)-held:raise ValueError('Whole batch must fit existing allowance')
   ledger.update(status='active',active_request_allowlist=keys,active_audit_manifest_sha256=fingerprint(plan),audit_scope='Registered earlier-token validation summaries only');write_json(a.budget_file,ledger)
  try:
   path=a.out/f'batch-{index}-jobs.json';write_json(path,{'jobs':batch});run_jobs('gpt54lowreference',path,a.out/'reader',a.credential_file,a.budget_file)
   for j in batch:
    result=json.loads((a.out/'reader/results'/(j['request_id']+'.json')).read_text());v=result.get('judgment',{})
    if result.get('status')!='ok' or set(v)!={'interpretation'} or not isinstance(v['interpretation'],str) or not v['interpretation'].strip():raise ValueError('Unavailable summary; stop dispatch without retry')
  finally:
   ledger=pause_budget(a.budget_file);write_json(a.out/f'batch-{index}-cost.json',{k:ledger.get(k) for k in ['status','spent_microusd','reserved_microusd']})
 write_json(a.out/'complete.json',{'unique_summaries':128,'cohorts':HASHES,'scope':'Schema-valid validation summaries. Semantic fidelity not established.'})


if __name__=='__main__':main()
