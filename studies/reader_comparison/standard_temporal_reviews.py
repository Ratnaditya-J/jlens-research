"""Fixed during/after-action validation reviews; unchanged accepted readers and bounded spend."""
import argparse,importlib,json,math
from pathlib import Path
CANDIDATES = [('gpt41reference','reference'),('gpt54standardreference','standardreference')]
from audit_budgeted_reader import pause_budget
from budgeted_api_client import file_lock
from collect_local_readers import load_jobs,load_results,valid_score
from contracts import fingerprint
from finish_primary_with_missing import verify_result
from smoke import digest,write_json
from verify_reader_acceptance import load_acceptance as load_original_acceptance
from verify_standard_acceptance import load_acceptance as load_standard_acceptance

def load_acceptance(path,manifest):
 return (load_standard_acceptance if manifest['kind']=='bounded-hosted-standardreference-reader-v1' else load_original_acceptance)(path,manifest)


def activate(path,plan):
 keys=plan['request_allowlist']
 if plan['kind']!='accepted-temporal-validation-reviews-v1' or not 1<=len(keys)<=32 or len(set(keys))!=len(keys):raise ValueError('Wrong bounded temporal validation batch')
 with file_lock(str(path)+'.lock'):
  ledger=json.loads(path.read_text());held=ledger.get('reserved_microusd',0)
  if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=20:raise ValueError('Paused registered$20 allowance required')
  if held!=sum(r['reserved_microusd'] for r in ledger['records'].values() if r['status']=='reserved'):raise ValueError('Unknown accounting changed')
  if any(r['request_sha256'] in keys for r in ledger['records'].values()):raise ValueError('No retries')
  if not 0<plan['maximum_reserved_microusd']<=20_000_000-held-ledger.get('spent_microusd',0):raise ValueError('Whole batch must fit allowance')
  ledger.update(status='active',active_request_allowlist=keys,active_audit_manifest_sha256=fingerprint(plan),audit_scope='Fixed during/after-action validation review requests only');write_json(path,ledger)


def main():
 p=argparse.ArgumentParser()
 for n in ['budget-file','credential-file','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--dry-run',action='store_true')
 a=p.parse_args();root=Path('runs/reader-comparison');union={};sources={};ledger=json.loads(a.budget_file.read_text())
 if not ledger['status'].startswith('paused'):raise ValueError('Prior paid coordinator must complete first')
 completion=root/'accepted-during-after-validation-summaries-final47/complete.json'
 if not completion.exists():raise ValueError('Temporal summary coordinator must finish first; no concurrent dispatch')
 complete=json.loads(completion.read_text())
 if complete.get('attempted_summaries')!=428 or complete.get('usable_summaries')!=427 or len(complete.get('missing',[]))!=1:raise ValueError('Expected full temporal summary accounting with diagnosed timeout')
 for path,sha in complete['source_hashes'].items():
  if digest(path)!=sha:raise ValueError('Temporal summary receipt/source changed')
 sources[str(completion)]=digest(completion)
 recorded=json.loads(Path('studies/reader_comparison/evidence/accepted-primary-end-prompt-calibration.json').read_text())['endpoints']
 lockpath=root/'accepted-calibration-before_action/lock.json';lock=json.loads(lockpath.read_text())
 if digest(lockpath)!=recorded['before_action']['lock_sha256']:raise ValueError('Original calibration lock changed')
 for path,sha in lock['source_hashes'].items():
  if digest(path)!=sha:raise ValueError('Frozen calibration source changed')
 expected={'during_action': '4ec4619298dc5c6f538a5d5088d9d90afe33bc0118a91ff1eb78a81cbc43b70b', 'after_action': '9874abc3789ce87a1fb7b224c9b73bb07b5a6ad39417281b784fa2df8314db7f'}
 for endpoint,expected_sha in expected.items():
  directory=root/('accepted-validation-'+endpoint)/'reviews';m,jobs,aliases=load_jobs(directory)
  if digest(directory/'jobs.json')!=expected_sha:raise ValueError('Fixed temporal validation jobs changed')
  if m['phase']!='validation' or m['stage']!='reviews' or m['endpoint']!=endpoint or m['subject_identity']!=lock['identity'] or m['interpreter_code_sha256']!=lock['interpreter_code_sha256']:raise ValueError('Wrong temporal validation cohort')
  if len(aliases)!=1134 or len({x['episode_id'] for x in aliases})!=126:raise ValueError('Expected full126-episode nine-arm cohort')
  if sum(x['request_id'] is None for x in aliases)!=(5 if endpoint=='during_action' else 0):raise ValueError('Summary missingness changed')
  for j in jobs:
   if j['request_id'] in union and union[j['request_id']]!=j:raise ValueError('Request collision')
   union[j['request_id']]=j
  for path in [lockpath,directory/'manifest.json',directory/'jobs.json',directory/'aliases.json']:sources[str(path)]=digest(path)
 jobs=sorted(union.values(),key=lambda j:j['request_id']);attempted={r['request_sha256'] for r in ledger['records'].values()};pending={};initial={}
 for c,s in CANDIDATES:
  runner=importlib.import_module('hosted_text_reader_'+s);transport=importlib.import_module('budgeted_hosted_'+s)
  acceptance=Path('studies/reader_comparison/evidence')/('hosted-'+c+'-acceptance'+('-v2' if s=='reference' else '')+'.json');sources.update(load_acceptance(acceptance,runner.execution_manifest(c)))
  roots=[root/('hosted-'+c+'-coverage')/'reader']+[root/name/c for name in ['accepted-primary-validation-reviews-first64','accepted-primary-validation-reviews-remaining188','accepted-primary-validation-reviews-final76','accepted-primary-test-reviews','accepted-primary-test-reviews-final26','accepted-early-validation-reviews','accepted-temporal-validation-reviews','accepted-temporal-validation-reviews-continuation','accepted-temporal-validation-reviews-authorized20','accepted-temporal-validation-reviews-after-outage']]
  if c=='gpt54standardreference':roots=[root/'hosted-gpt54standardreference-coverage/reader']
  results={}
  for prior in roots:
   manifest,found=load_results(prior,jobs)
   if manifest!=runner.execution_manifest(c):raise ValueError('Cached execution differs')
   for rid,result in found.items():
    if rid in results and result!=results[rid]:raise ValueError('Conflicting cached outputs')
    results[rid]=result;sources[str(prior/'results'/(rid+'.json'))]=digest(prior/'results'/(rid+'.json'))
  pending[c]=[]
  for j in jobs:
   key=fingerprint(transport.payload(c,j['system'],j['evidence']))
   if key in attempted:
    if j['request_id'] not in results:raise ValueError('Attempted request lacks reusable result; no retry')
    path,sha=verify_result(j,results[j['request_id']],roots,c,s,ledger);sources[path]=sha
   else:
    if j['request_id'] in results:raise ValueError('Unaccounted cache result')
    pending[c].append(j)
  initial[c]=results
 if len(jobs)!=960:raise ValueError('Expected full960-request temporal validation union')
 if any(len(pending[c])!={'gpt41reference':579,'gpt54standardreference':924}[c] for c,_ in CANDIDATES):raise ValueError('Expected579 original GPT4 and924 standard-route GPT5 never-attempted requests')
 if a.dry_run:
  print(json.dumps({'pending':{c:len(x) for c,x in pending.items()},'cached':{c:len(x) for c,x in initial.items()}}));return
 if a.out.exists():raise ValueError('Preserve prior run; no automatic restart')
 a.out.mkdir(parents=True);write_json(a.out/'registration.json',{'jobs':jobs,'pending':pending,'source_hashes':sources,'code_sha256':digest(__file__),'scope':'Distinct standard-route temporal protocol: GPT4 original exact execution plus qualified GPT5 standard route, with original Flex summaries retained. No Flex judgments substituted into this protocol. No threshold fitting or test aggregation. Batch size at most16 per reader chosen only by remaining monetary allowance. No score-dependent selection, retries, fallback, cap increase or outcome aggregation.'})
 for c,s in CANDIDATES:
  out=a.out/c;out.mkdir();(out/'results').mkdir();write_json(out/'manifest.json',importlib.import_module('hosted_text_reader_'+s).execution_manifest(c))
  for rid,result in initial[c].items():write_json(out/'results'/(rid+'.json'),result)
 index=0
 while any(pending.values()):
  ledger=json.loads(a.budget_file.read_text());available=20_000_000-ledger.get('spent_microusd',0)-ledger.get('reserved_microusd',0)
  for size in range(1,0,-1):
   selected={c:pending[c][:size] for c,_ in CANDIDATES};keys=[];maximum=0
   for c,s in CANDIDATES:
    t=importlib.import_module('budgeted_hosted_'+s)
    for j in selected[c]:
     request=t.payload(c,j['system'],j['evidence']);keys.append(fingerprint(request));maximum+=math.ceil(t.reservation(c,request)*1e6)
   if maximum<=available:break
  else:raise ValueError('Even minimum fully reserved batch cannot fit; no cap increase')
  plan={'kind':'accepted-temporal-validation-reviews-v1','request_allowlist':keys,'maximum_reserved_microusd':maximum,'index':index};write_json(a.out/f'batch-{index}-plan.json',plan);activate(a.budget_file,plan)
  try:
   for c,s in CANDIDATES:
    if not selected[c]:continue
    if json.loads(a.budget_file.read_text())['status']!='active':raise ValueError('Budget/provider pause')
    path=a.out/f'{c}-batch-{index}-jobs.json';write_json(path,{'jobs':selected[c]});importlib.import_module('hosted_text_reader_'+s).run_jobs(c,path,a.out/c,a.credential_file,a.budget_file)
    ledger=json.loads(a.budget_file.read_text())
    for j in selected[c]:
     result=json.loads((a.out/c/'results'/(j['request_id']+'.json')).read_text());path,sha=verify_result(j,result,[a.out/c],c,s,ledger);sources[path]=sha
    pending[c]=pending[c][len(selected[c]):]
  finally:
   ledger=pause_budget(a.budget_file);write_json(a.out/f'batch-{index}-cost.json',{k:ledger.get(k) for k in ['status','spent_microusd','reserved_microusd']})
  index+=1
 counts={}
 for c,_ in CANDIDATES:
  _,results=load_results(a.out/c,jobs)
  if len(results)!=len(jobs):raise ValueError('Incomplete accounting')
  counts[c]={'attempted':len(jobs),'usable':sum(valid_score(r) is not None for r in results.values())}
 write_json(a.out/'complete.json',{'coverage':counts,'source_hashes':sources,'scope':'During/after-action validation requests accounted for with explicit unavailable replies. Endpoint-specific calibration and subsequent held-out inference remain separate steps.'})


if __name__=='__main__':main()
