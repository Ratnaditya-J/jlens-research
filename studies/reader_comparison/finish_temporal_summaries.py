"""Continue only never-attempted temporal summaries, preserving one diagnosed timeout."""
import argparse,json,math,shutil
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
 write_json(a.out/'registration.json',{'cohorts':HASHES,'source_hashes':sources,'code_sha256':digest(__file__),'scope':'47 never-attempted during/after-action validation summaries; reuse380 verified successes and preserve one timeout. Content-hash-ordered fully reserved batches of at most32. Same accepted execution. No reviews, retries, fallback, cap increase or held-out access.'})
 audit_path=Path('studies/reader_comparison/evidence/temporal-summary-budget-stop-audit.json')
 prior=json.loads(audit_path.read_text())
 for path,sha in prior['source_hashes'].items():
  if digest(path)!=sha:raise ValueError('Stopped summary source changed')
 ledger=json.loads(a.budget_file.read_text())
 if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=8:raise ValueError('Paused unchanged allocation required')
 if prior['usable_verified']!=380 or len(prior['missing'])!=1 or len(prior['never_attempted_ids'])!=47:raise ValueError('Wrong stopped cohort')
 for entry in prior['missing']:
  record=ledger['records'][entry['reservation_id']]
  if record['status']!='reserved' or record['reserved_microusd']!=entry['reserved_microusd'] or record['request_sha256']!=entry['api_request_sha256']:raise ValueError('Timeout reservation changed')
 old=root/'accepted-during-after-validation-summaries-continuation/reader'
 for sub in ['results','api-cache']:
  (a.out/'reader'/sub).mkdir(parents=True,exist_ok=True)
  for f in (old/sub).glob('*.json'):shutil.copy2(f,a.out/'reader'/sub/f.name)
 shutil.copy2(old/'manifest.json',a.out/'reader/manifest.json')
 sources.update(prior['source_hashes']);sources[str(audit_path)]=digest(audit_path)
 pending=[j for j in jobs if j['request_id'] in set(prior['never_attempted_ids'])]
 if len(pending)!=47:raise ValueError('Wrong continuation union')
 index=0
 while pending:
  ledger=json.loads(a.budget_file.read_text());available=8_000_000-ledger.get('spent_microusd',0)-ledger.get('reserved_microusd',0)
  for size in range(min(32,len(pending)),0,-1):
   batch=pending[:size];requests=[payload('gpt54lowreference',j['system'],j['evidence']) for j in batch];keys=[fingerprint(r) for r in requests];maximum=sum(math.ceil(reservation('gpt54lowreference',r)*1e6) for r in requests)
   if maximum<=available:break
  else:raise ValueError('Minimum summary reservation unaffordable; no cap increase')
  plan={'index':index,'request_allowlist':keys,'maximum_reserved_microusd':maximum,'cohorts':HASHES};write_json(a.out/f'batch-{index}-plan.json',plan)
  with file_lock(str(a.budget_file)+'.lock'):
   ledger=json.loads(a.budget_file.read_text());held=ledger.get('reserved_microusd',0)
   if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=8:raise ValueError('Paused registered$8 allocation required')
   if held!=sum(r['reserved_microusd'] for r in ledger['records'].values() if r['status']=='reserved'):raise ValueError('Unknown accounting changed')
   if any(r['request_sha256'] in keys for r in ledger['records'].values()):raise ValueError('No retries')
   if maximum>8_000_000-ledger.get('spent_microusd',0)-held:raise ValueError('Whole batch must fit existing allowance')
   ledger.update(status='active',active_request_allowlist=keys,active_audit_manifest_sha256=fingerprint(plan),audit_scope='Registered during/after-action validation summaries only');write_json(a.budget_file,ledger)
  try:
   path=a.out/f'batch-{index}-jobs.json';write_json(path,{'jobs':batch});run_jobs('gpt54lowreference',path,a.out/'reader',a.credential_file,a.budget_file)
   receipt=audit(path,a.out/'reader',a.budget_file,'gpt54lowreference','lowreference');write_json(a.out/f'batch-{index}-receipts.json',receipt);sources.update(receipt['source_hashes'])
  finally:
   ledger=pause_budget(a.budget_file);write_json(a.out/f'batch-{index}-cost.json',{k:ledger.get(k) for k in ['status','spent_microusd','reserved_microusd']})
  pending=pending[len(batch):];index+=1
 write_json(a.out/'complete.json',{'attempted_summaries':428,'usable_summaries':427,'missing':prior['missing'],'cohorts':HASHES,'source_hashes':sources,'scope':'427 usable validation summaries and one preserved timeout with uncertain charge. Raw successful receipts verified; missing aliases retained. Semantic fidelity not established.'})


if __name__=='__main__':main()
