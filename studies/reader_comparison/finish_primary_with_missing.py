"""Continue only unattempted validation requests; preserve observed missingness."""
import argparse,importlib,json,math
from pathlib import Path
from accepted_review_tranche import CANDIDATES,JOBS_SHA
from complete_primary_validation_reviews import activate,KIND
from audit_budgeted_reader import pause_budget
from collect_local_readers import load_jobs,load_results,valid_score
from contracts import fingerprint
from smoke import digest,write_json
from verify_accepted_review_receipts import verify_one
from verify_reader_acceptance import load_acceptance


def verify_result(job,result,roots,candidate,suffix,ledger):
 transport=importlib.import_module('budgeted_hosted_'+suffix)
 runner=importlib.import_module('hosted_text_reader_'+suffix)
 request=transport.payload(candidate,job['system'],job['evidence']);key=fingerprint(request)
 matches=[p for root in roots for p in (root/'api-cache').glob(key+'-raw-*.json')]
 if len(matches)!=1:raise ValueError('Need exactly one original receipt')
 path=matches[0];raw=json.loads(path.read_text());record=ledger['records'][raw['budget_reservation']]
 if result.get('status')=='ok':verify_one(job,result,raw,record,candidate,suffix)
 else:
  if result.get('request_id')!=job['request_id'] or result.get('manifest_sha256')!=fingerprint(runner.execution_manifest(candidate)):raise ValueError('Unavailable identity changed')
  response=raw['response'];c=transport.CONFIGS[candidate]
  if raw['request']!=request or response.get('model') not in c['response_models'] or response.get('provider')!=c['provider']:raise ValueError('Unavailable request/provider changed')
  if response['choices'][0]['finish_reason']!='length' or result.get('error_type')!='ValueError':raise ValueError('New failure needs investigation')
  if record['request_sha256']!=key or record['status']!='settled' or record['response_id']!=response['id'] or record['actual_microusd']!=math.ceil(float(response['usage']['cost'])*1e6):raise ValueError('Missing-result settlement changed')
 return str(path),digest(path)


def main():
 p=argparse.ArgumentParser()
 for n in ['budget-file','credential-file','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();root=Path('runs/reader-comparison');jobsdir=root/'accepted-primary-validation/reviews';m,jobs,_=load_jobs(jobsdir)
 if m['phase']!='validation' or digest(jobsdir/'jobs.json')!=JOBS_SHA:raise ValueError('Wrong fixed cohort')
 ledger=json.loads(a.budget_file.read_text())
 if not ledger['status'].startswith('paused'):raise ValueError('Prior inference must be terminal')
 attempted={r['request_sha256'] for r in ledger['records'].values()};pending={};initial={};sources={};readers={}
 for candidate,suffix in CANDIDATES:
  runner=importlib.import_module('hosted_text_reader_'+suffix);transport=importlib.import_module('budgeted_hosted_'+suffix)
  acceptance=Path('studies/reader_comparison/evidence')/('hosted-'+candidate+'-acceptance'+('-v2' if suffix=='reference' else '')+'.json')
  sources.update(load_acceptance(acceptance,runner.execution_manifest(candidate)))
  prior=root/'accepted-primary-validation-reviews-remaining188'/candidate
  roots=[root/('hosted-'+candidate+'-coverage')/'reader',root/'accepted-primary-validation-reviews-first64'/candidate,prior]
  manifest,results=load_results(prior,jobs)
  if manifest!=runner.execution_manifest(candidate):raise ValueError('Changed execution')
  for job in jobs:
   key=fingerprint(transport.payload(candidate,job['system'],job['evidence']))
   if (key in attempted)!=(job['request_id'] in results):raise ValueError('Ledger/result discrepancy; no retry')
   if job['request_id'] in results:
    path,sha=verify_result(job,results[job['request_id']],roots,candidate,suffix,ledger);sources[path]=sha
    path=prior/'results'/(job['request_id']+'.json');sources[str(path)]=digest(path)
  pending[candidate]=[j for j in sorted(jobs,key=lambda x:x['request_id']) if j['request_id'] not in results];initial[candidate]=results;readers[candidate]=roots
 if [len(pending[c]) for c,_ in CANDIDATES]!=[30,46]:raise ValueError('Expected exact76 unattempted requests')
 if a.out.exists():raise ValueError('No automatic restart')
 a.out.mkdir(parents=True);write_json(a.out/'registration.json',{'pending':pending,'source_hashes':sources,'code_sha256':digest(__file__),'scope':'Exactly76 never-attempted primary validation requests. Same accepted readers, known truncation retained unavailable. No retry, cap increase, threshold changes or held-out scoring.'})
 for candidate,suffix in CANDIDATES:
  out=a.out/candidate;out.mkdir();(out/'results').mkdir();write_json(out/'manifest.json',importlib.import_module('hosted_text_reader_'+suffix).execution_manifest(candidate))
  for rid,result in initial[candidate].items():write_json(out/'results'/(rid+'.json'),result)
 for index,start in enumerate(range(0,46,16)):
  batches={c:pending[c][start:start+16] for c,_ in CANDIDATES};keys=[];maximum=0
  for c,s in CANDIDATES:
   t=importlib.import_module('budgeted_hosted_'+s)
   for j in batches[c]:
    request=t.payload(c,j['system'],j['evidence']);keys.append(fingerprint(request));maximum+=math.ceil(t.reservation(c,request)*1e6)
  plan={'kind':KIND,'jobs_sha256':JOBS_SHA,'request_allowlist':keys,'maximum_reserved_microusd':maximum,'scope':'Previously unattempted primary validation requests only; observed truncation retained unavailable.'};write_json(a.out/f'batch-{index}-plan.json',plan);activate(a.budget_file,plan)
  try:
   for c,s in CANDIDATES:
    if not batches[c]:continue
    if json.loads(a.budget_file.read_text())['status']!='active':raise ValueError('Provider/budget pause')
    path=a.out/f'{c}-batch-{index}-jobs.json';write_json(path,{'jobs':batches[c]});importlib.import_module('hosted_text_reader_'+s).run_jobs(c,path,a.out/c,a.credential_file,a.budget_file)
    ledger=json.loads(a.budget_file.read_text())
    for j in batches[c]:
     result=json.loads((a.out/c/'results'/(j['request_id']+'.json')).read_text());p,sha=verify_result(j,result,[a.out/c],c,s,ledger);sources[p]=sha
  finally:
   ledger=pause_budget(a.budget_file);write_json(a.out/f'batch-{index}-cost.json',{k:ledger.get(k) for k in ['status','spent_microusd','reserved_microusd']})
 counts={}
 for c,_ in CANDIDATES:
  _,results=load_results(a.out/c,jobs)
  if len(results)!=144:raise ValueError('Not all requests accounted for')
  counts[c]={'attempted':144,'usable':sum(valid_score(r) is not None for r in results.values())}
 write_json(a.out/'complete.json',{'jobs_sha256':JOBS_SHA,'coverage':counts,'receipt_source_hashes':sources,'scope':'All validation requests accounted for; unavailable judgments retained. Not a detector performance or semantic validity result.'})


if __name__=='__main__':main()
