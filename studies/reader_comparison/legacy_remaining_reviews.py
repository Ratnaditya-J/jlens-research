"""Guarded exact legacy reviewer requests and immediate frozen analysis handoff."""
import argparse,concurrent.futures,json,math,subprocess,sys,time,urllib.request
from pathlib import Path
from contracts import fingerprint,parse_json_reply
from budgeted_api_client import reserve,settle,file_lock
from smoke import digest,write_json
ROOT=Path(__file__).resolve().parents[2]
PRICES={'openai/gpt-4.1':(2,8),'openai/gpt-5.4':(2.5,15)}
MEANS={'openai/gpt-4.1':.006150663840096911,'openai/gpt-5.4':.01081162733856367}
def payload(j):
 p={'model':j['model'],'messages':[{'role':'system','content':j['system']},{'role':'user','content':json.dumps(j['evidence'],ensure_ascii=False)}],'response_format':{'type':'json_object'},'max_tokens':1600,'provider':{'require_parameters':True}}
 if j['model'].startswith('openai/gpt-5'):p['reasoning']={'effort':'low'}
 else:p['temperature']=0
 return p
def amount(p):
 pp,cp=PRICES[p['model']];return ((2*sum(len(m['content'].encode()) for m in p['messages'])+2048)*pp+3200*cp)/1e6
def valid(d):
 j=d['judgment']
 return type(j.get('score')) is int and j['score'] in [0,1,2] and j.get('confidence') in ['high','medium','low'] and all(k in j for k in ['evidence','rationale','limitations'])
def main():
 p=argparse.ArgumentParser();p.add_argument('--budget-file',type=Path,required=True);p.add_argument('--credential-file',type=Path,required=True);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 prep=ROOT/'runs/reader-comparison/legacy-remaining-review-preparation';done=json.loads((prep/'complete.json').read_text());sources={str(prep/'complete.json'):digest(prep/'complete.json')}
 for path,h in done['source_hashes'].items():
  if digest(path)!=h:raise ValueError('Preparation source changed')
  sources[path]=h
 lp=ROOT/'runs/fresh-jsummary-calibration/lock.json';lock=json.loads(lp.read_text())
 for path,h in lock['source_hashes'].items():
  if digest(ROOT/path)!=h:raise ValueError('Frozen calibration source changed')
 sources[str(lp)]=digest(lp);cohorts={};jobs={};cache=ROOT/'runs/jsummary-api-cache'
 for panel in ['template-challenge','fresh-completion']:
  f=prep/(panel+'.json');cohorts[panel]=json.loads(f.read_text());sources[str(f)]=digest(f);d=ROOT/f'runs/{panel}-jsummary-test'
  for name in ['summary-manifest.json','summaries.json','summary-complete.json','review-manifest.json']:sources[str(d/name)]=digest(d/name)
  if json.loads((d/'review-manifest.json').read_text())!=cohorts[panel]['manifest']:raise ValueError('Review manifest changed')
  if digest(d/'summaries.json')!=cohorts[panel]['manifest']['summaries_sha256']:raise ValueError('Summaries changed')
  if (d/'review-complete.json').exists():raise ValueError('Preserve prior reviews')
  for name in ['cases.json','baseline-cases.json']:
   original=ROOT/f'reports/{panel}-comparison'/name;sources[str(original)]=digest(original)
  for j in cohorts[panel]['jobs']:
   v=payload(j);jobs[fingerprint(v)]=v
 with urllib.request.urlopen('https://openrouter.ai/api/v1/models',timeout=30) as r:catalog=json.load(r)
 pricing={}
 for model,(pp,cp) in PRICES.items():
  e=next(x for x in catalog['data'] if x['id']==model);pricing[model]=e['pricing']
  if float(e['pricing']['prompt'])>pp/1e6 or float(e['pricing']['completion'])>cp/1e6:raise ValueError('Price above planning allowance')
 ledger=json.loads(a.budget_file.read_text());attempted={r['request_sha256'] for r in ledger['records'].values()};cached={};missing={};pending={}
 for key,request in jobs.items():
  f=cache/(key+'.json')
  if f.exists():
   d=json.loads(f.read_text())
   if d.get('request')!=request or d['request_sha256']!=key or d['requested_model']!=request['model']:raise ValueError('Cache identity mismatch')
   if valid(d):cached[key]=d
   else:missing[key]='Invalid original cached judgment'
  elif key in attempted or list(cache.glob(key+'-raw-*.json')):missing[key]='Previously attempted; no retry'
  else:pending[key]=request
 forecast=sum(MEANS[v['model']] for v in pending.values());available=(80_000_000-ledger['spent_microusd']-ledger['reserved_microusd'])/1e6
 plan={'scope':'Full template-challenge and original code-onset continuation panels; fresh-completion is a separate-output alias of original fresh cohort, preserving original partial results, five original arms, exact frozen reviewer payloads and unconstrained original provider routing. Shared single-attempt budget guard replaces original retry behavior. Catalog prices verified; no route/model/prompt substitution. Missing remains unavailable. Frozen original thresholds and evaluation unchanged.','source_hashes':sources,'code_sha256':digest(__file__),'pricing':pricing,'pending':pending,'cached':list(cached),'previously_missing':missing,'point_estimate_usd':forecast,'available_usd':available,'concurrency':8}
 out=ROOT/'runs/reader-comparison/legacy-remaining-reviews'
 if a.dry_run:print(json.dumps({'pending':len(pending),'cached':len(cached),'missing':len(missing),'point_estimate_usd':forecast,'available_usd':available}));return
 if out.exists():raise ValueError('Preserve prior run')
 if forecast>available:raise ValueError('Projected full panel work exceeds remaining allowance')
 with file_lock(str(a.budget_file)+'.lock'):
  b=json.loads(a.budget_file.read_text())
  if not b['status'].startswith('paused') or b['additional_limit_usd']!=80:raise ValueError('Expected idle80 budget')
  out.mkdir();write_json(out/'registration.json',plan);b.update(status='active',active_request_allowlist=list(pending),active_audit_manifest_sha256=fingerprint(plan),audit_scope=plan['scope']);write_json(a.budget_file,b)
 def one(key):
  reqdata=pending[key];token=reserve(a.budget_file,amount(reqdata),key)
  try:
   secret=json.loads(a.credential_file.read_text())['OPENROUTER_API_KEY'];req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(reqdata).encode(),headers={'Authorization':'Bearer '+secret,'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=180) as response:raw=json.load(response)
   write_json(cache/(key+'-raw-'+str(time.time_ns())+'.json'),{'request':reqdata,'response':raw,'budget_reservation':token});cost=raw.get('usage',{}).get('cost')
   if cost is None:raise ValueError('Unknown charge')
   settle(a.budget_file,token,float(cost),raw.get('id'))
   if raw.get('model')!=reqdata['model'] or raw['choices'][0].get('finish_reason')!='stop':raise ValueError('Unavailable model or finish reason')
   d={'request_sha256':key,'request':reqdata,'requested_model':reqdata['model'],'resolved_model':raw['model'],'provider':raw.get('provider'),'judgment':parse_json_reply(raw['choices'][0]['message']['content']),'usage':raw.get('usage'),'response_id':raw.get('id')}
   if not valid(d):raise ValueError('Invalid judgment')
   write_json(cache/(key+'.json'),d);return key,d,None
  except Exception as e:return key,None,type(e).__name__+': '+str(e)[:150]
 try:
  keys=iter(sorted(pending));cursor=0;failures=0;stop=False
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
   active={}
   def launch():
    key=next(keys,None)
    if key is not None:active[pool.submit(one,key)]=key
   for _ in range(8):launch()
   while active:
    finished,_=concurrent.futures.wait(active,return_when=concurrent.futures.FIRST_COMPLETED)
    for future in finished:
     key=active.pop(future)
     try:key,d,error=future.result()
     except Exception as exc:d=None;error=type(exc).__name__+': '+str(exc)[:150];stop=True
     cursor+=1
     if error:missing[key]=error;failures+=1
     else:cached[key]=d;failures=0
     if failures>=3:stop=True
     write_json(out/'progress.json',{'attempted':cursor,'total':len(pending),'usable':len(cached),'missing':missing,'dispatch_stopped':stop})
     if not stop:launch()
   if stop:raise ValueError('Dispatch stopped; all active requests drained, receipts retained')
  for panel,cohort in cohorts.items():
   rows={};errors=[]
   for j in cohort['jobs']:
    rows.setdefault(j['episode_id'],{'episode_id':j['episode_id']})
   for eid,row in rows.items():
    for arm in json.loads((ROOT/'configs/jsummary-v1.json').read_text())['arms']:
     pair=[j for j in cohort['jobs'] if j['episode_id']==eid and j['arm']==arm];found=[cached.get(fingerprint(payload(j))) for j in pair]
     if len(found)!=2 or any(d is None for d in found):row[arm]={'score':None,'missing':True}
     else:
      ss=[d['judgment']['score'] for d in found];row[arm]={'score':min(ss),'reviewer_scores':ss,'agreement':len(set(ss))==1,'request_sha256':[d['request_sha256'] for d in found]}
   for j in cohort['jobs']:
    key=fingerprint(payload(j))
    if key not in cached:errors.append({'episode_id':j['episode_id'],'arm':j['arm'],'model':j['model'],'error':missing.get(key,'Unavailable')})
   target=ROOT/f'runs/{panel}-jsummary-test';write_json(target/'scores.json',list(rows.values()));write_json(target/'review-complete.json',{'completed':len(cohort['jobs'])-len(errors),'total':len(cohort['jobs']),'errors':errors,'scores_sha256':digest(target/'scores.json'),'manifest_sha256':fingerprint(cohort['manifest'])})
  def evaluate(panel):
   with (out/(panel+'-evaluation.log')).open('w') as log:subprocess.run([sys.executable,str(ROOT/'scripts/evaluate_jsummary.py'),'--dataset',panel],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(evaluate,cohorts))
  write_json(out/'complete.json',{'panels':list(cohorts),'unique_usable':len(cached),'missing':missing,'evaluation_complete':True,'source_hashes':{str(ROOT/f'reports/jsummary-{p}/summary.json'):digest(ROOT/f'reports/jsummary-{p}/summary.json') for p in cohorts}})
 finally:
  with file_lock(str(a.budget_file)+'.lock'):
   b=json.loads(a.budget_file.read_text())
   if b['status']=='active':b['status']='paused_after_legacy_reviews'
   write_json(a.budget_file,b)
if __name__=='__main__':main()
