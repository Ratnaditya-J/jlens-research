"""Explicit OpenRouter transport supplement; preserve cached direct-API judgments.

The logical request stays unchanged; sent_request and transport record the actual
wire payload and provider. The original manifest identifies the base aggregation
contract; transport-manifest.json records this supplemental producer.
"""
import argparse,concurrent.futures,hashlib,json,os,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2)+'\n');t.replace(p)
def main():
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=12);p.add_argument('--phase',choices=['validation','test'],required=True);p.add_argument('--dataset',choices=['monitor-controls'],default='monitor-controls');p.add_argument('--offset',type=int,choices=[0,32,64],default=0);a=p.parse_args();suffix=f'-offset{a.offset}' if a.offset else '';stem={'primary':'fresh','template-challenge':'template-challenge','specificity-controls':'specificity-controls','monitor-controls':'monitor-controls'}[a.dataset];assert a.dataset=='primary' or a.phase=='test'
 if a.phase=='test':
  lockp=ROOT/f'runs/fresh{suffix}-calibration/lock.json';assert lockp.exists(),'Lock calibration before test interpretation'
  lockdata=json.loads(lockp.read_text())
  for name,digest in lockdata['source_hashes'].items():assert sha(ROOT/name)==digest
 credentials=Path('/workspace/private/openrouter-credentials.json')
 api_key=json.loads(credentials.read_text())['OPENROUTER_API_KEY']
 routes={'gpt-4.1-2025-04-14':('openai/gpt-4.1','openai/gpt-4.1-2025-04-14'),'gpt-5.4':('openai/gpt-5.4','openai/gpt-5.4-20260305')}
 with urllib.request.urlopen('https://openrouter.ai/api/v1/models',timeout=30) as response:catalog=json.load(response)
 models={x['id']:x for x in catalog['data']}
 for model,(route,canonical) in routes.items():assert models[route]['canonical_slug']==canonical
 assert a.offset==0 and a.dataset=='monitor-controls', 'Separate frozen monitor control interpretation only'
 cfgpath=ROOT/'configs/jview-final-v1.json';cfg=json.loads(cfgpath.read_text());vp=ROOT/f'runs/{stem}{suffix}-assembled/{a.phase}-readouts.json';tp=ROOT/f'runs/{stem}{suffix}-assembled/{a.phase}-contexts.json'
 views=json.loads(vp.read_text());texts={x['episode_id']:x for x in json.loads(tp.read_text())['rows']};out=ROOT/f'runs/{stem}{suffix}-jview-{a.phase}';out.mkdir(parents=True,exist_ok=True)
 import fcntl
 lock=(out/'lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 manifest={'config_sha256':sha(cfgpath),'readouts_sha256':sha(vp),'contexts_sha256':sha(tp),'script_sha256':sha(Path(__file__)),'scope':cfg['scope']}
 m=out/'manifest.json'
 if m.exists():assert json.loads(m.read_text())==manifest,'changed scoring inputs'
 else:write(m,manifest)
 transport_manifest={'base_manifest_sha256':sha(m),'supplement_script_sha256':sha(Path(__file__)),'routes':routes,'catalog_canonical_slugs':{v[0]:models[v[0]]['canonical_slug'] for v in routes.values()},'scope':'Secondary monitor-control interpretation via OpenRouter; original frozen J rubric unchanged. OpenRouter catalog snapshot mapping and OpenAI-only routing do not prove bitwise provider equivalence. Preserve provider-specific sensitivity analysis.'}
 tm=out/'transport-manifest.json'
 if tm.exists():assert json.loads(tm.read_text())==json.loads(json.dumps(transport_manifest))
 else:write(tm,transport_manifest)
 # Preserve any prior incomplete score aggregation before filling missing requests.
 for name in ['complete.json','scores.json']:
  prior=out/name
  if prior.exists():
   archive=out/'pre-transport-archive'/(sha(prior)+'-'+name)
   if not archive.exists():write(archive,json.loads(prior.read_text()))
 jobs=[]
 for v in views:
  eid=v['episode_id'];alias=hashlib.sha256(eid.encode()).hexdigest()[:16];context=texts[eid]
  for arm in cfg['arms']:
   evidence={'case':alias,'arm':arm,'task_context':context['prompt'],'available_generated_prefix':context['generated_prefix']}
   if arm=='jview':
    evidence['jspace_layers']=[{'layer':l['layer'],'top_tokens':[{'id':t['id'],'text':t['text'],'logit':round(t['logit'],3)} for t in l['top_tokens'][:20]],'candidate_ranks':[{'id':t['id'],'text':t['text'],'rank':t['rank'],'logit':round(t['logit'],3)} for t in l['candidate_ranks']]} for l in v['layers']]
   for model in cfg['models']:jobs.append((eid,arm,model,evidence))
 def review(job):
  eid,arm,model,evidence=job;path=out/'reviews'/eid/(arm+'-'+model+'.json')
  system=cfg['rubric']+'\nSCORING DEFINITION: '+cfg[arm+'_score']
  payload={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(evidence,ensure_ascii=False)}],'response_format':{'type':'json_object'},'max_completion_tokens':2000,'store':False}
  if model.startswith('gpt-5'):payload['reasoning_effort']='low'
  else:payload['temperature']=0
  digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
  if path.exists():
   saved=json.loads(path.read_text());assert saved['request_sha256']==digest;return saved
  sent={**payload,'model':routes[model][0],'max_tokens':payload['max_completion_tokens'],'provider':{'order':['OpenAI'],'allow_fallbacks':False}}
  del sent['max_completion_tokens']
  if 'reasoning_effort' in sent:sent['reasoning']={'effort':sent.pop('reasoning_effort')}
  req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(sent).encode(),headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'})
  unavailable=out/'unavailable'/eid/(arm+'-'+model+'.json')
  if unavailable.exists():raise RuntimeError('Documented unavailable response; no bypass')
  started=time.time()
  for attempt in range(5):
   try:
    with urllib.request.urlopen(req,timeout=120) as response:raw=json.load(response)
    assert raw['model']==routes[model][0] and raw.get('provider')=='OpenAI','Unexpected provider/model route'
    choice=raw['choices'][0]
    if choice.get('finish_reason')=='error' or choice.get('error') or choice['message'].get('refusal'):
     write(unavailable,{'raw_response':raw,'sent_request':sent,'request_sha256':digest});raise RuntimeError('Provider unavailable; retain missing judgment')
    judgment=json.loads(choice['message']['content']);assert type(judgment['score']) is int and judgment['score'] in [0,1,2];assert judgment['confidence'] in ['high','medium','low']
    for key in ['evidence','rationale','limitations']:assert key in judgment
    break
   except (urllib.error.URLError,TimeoutError,ValueError,AssertionError,KeyError,TypeError) as error:
    if isinstance(error,urllib.error.HTTPError) and error.code not in [429,500,502,503,504]:raise
    if attempt==4:raise
    time.sleep(2**attempt)
  saved={'episode_id':eid,'arm':arm,'requested_model':model,'resolved_model':raw['model'],'request_sha256':digest,'request':payload,'sent_request':sent,'sent_request_sha256':hashlib.sha256(json.dumps(sent,sort_keys=True).encode()).hexdigest(),'transport':{'gateway':'OpenRouter','provider':raw.get('provider'),'canonical_slug':routes[model][1],'manifest_sha256':sha(tm)},'judgment':judgment,'usage':raw.get('usage'),'response_id':raw['id'],'elapsed_seconds':time.time()-started}
  write(path,saved);return saved
 errors=[];completed=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
  futures={pool.submit(review,j):j for j in jobs}
  for future in concurrent.futures.as_completed(futures):
   job=futures[future]
   try:future.result();completed+=1
   except Exception as error:errors.append({'episode_id':job[0],'arm':job[1],'model':job[2],'error_type':type(error).__name__,'http_status':getattr(error,'code',None)})
   write(out/'progress.json',{'completed_calls':completed,'total_calls':len(jobs),'errors':errors})
 rows=[]
 for v in views:
  eid=v['episode_id'];row={'episode_id':eid}
  for arm in cfg['arms']:
   files=[out/'reviews'/eid/(arm+'-'+model+'.json') for model in cfg['models']]
   if not all(p.exists() for p in files):row[arm]={'score':None,'missing':True};continue
   js=[json.loads(p.read_text()) for p in files];scores=[j['judgment']['score'] for j in js]
   row[arm]={'score':min(scores),'reviewer_scores':scores,'agreement':scores[0]==scores[1],'review_sha256':[sha(p) for p in files]}
  rows.append(row)
 write(out/'scores.json',rows);write(out/'complete.json',{'episodes':len(rows),'completed_calls':completed,'expected_calls':len(jobs),'errors':errors,'scores_sha256':sha(out/'scores.json'),'manifest':manifest})
 print(json.dumps({'completed_calls':completed,'errors':errors}),flush=True)
if __name__=='__main__':main()
