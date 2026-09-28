"""Exact legacy summary payloads with eight workers and shared single-attempt budget."""
import argparse,concurrent.futures,importlib.util,json,math,time,urllib.request
from pathlib import Path
from contracts import fingerprint,parse_json_reply
from budgeted_api_client import reserve,settle,file_lock
from smoke import digest,write_json
ROOT=Path(__file__).resolve().parents[2]
def payload(model,system,evidence):
 return {'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(evidence,ensure_ascii=False)}],'response_format':{'type':'json_object'},'max_tokens':1600,'provider':{'require_parameters':True},'temperature':0}
def main():
 p=argparse.ArgumentParser();p.add_argument('--budget-file',type=Path,required=True);p.add_argument('--credential-file',type=Path,required=True);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 cfgp=ROOT/'configs/jsummary-v1.json';cfg=json.loads(cfgp.read_text());original=ROOT/'scripts/summarize_jviews.py';spec=importlib.util.spec_from_file_location('legacy_summarizer',original);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 lp=ROOT/'runs/fresh-jsummary-calibration/lock.json';lock=json.loads(lp.read_text())
 for path,expected in lock['source_hashes'].items():
  if digest(ROOT/path)!=expected:raise ValueError('Frozen source changed')
 cache=ROOT/'runs/jsummary-api-cache';jobs={};aliases={};manifests={};sources={str(cfgp):digest(cfgp),str(original):digest(original),str(lp):digest(lp)}
 for panel in ['template-challenge']:
  source=ROOT/f'runs/{panel}-assembled/test-readouts.json';sources[str(source)]=digest(source);views=json.loads(source.read_text());aliases[panel]=[]
  manifests[panel]={'readouts_sha256':digest(source),'config_sha256':digest(cfgp),'script_sha256':digest(original),'scope':'Per-layer blind summary; no labels, context, candidate ranks or other-reader outputs'}
  out=ROOT/f'runs/{panel}-jsummary-test'
  if out.exists():raise ValueError('Preserve prior panel output')
  for v in views:
   for layer in v['layers']:
    bag=' | '.join(f"{t['text']} ({t['logit']:.2f})" for t in layer['top_tokens'][:10]);request=payload(cfg['summarizer_model'],mod.PROMPT+' Return JSON with exactly one nonempty string field: interpretation.',{'TOKEN READOUTS':bag});key=fingerprint(request);jobs[key]=request;aliases[panel].append({'episode_id':v['episode_id'],'layer':layer['layer'],'key':key})
 with urllib.request.urlopen('https://openrouter.ai/api/v1/models',timeout=30) as r:catalog=json.load(r)
 entry=next(x for x in catalog['data'] if x['id']==cfg['summarizer_model']);prices=entry['pricing'];pp=float(prices['prompt']);cp=float(prices['completion'])
 if pp>1e-6 or cp>4e-6:raise ValueError('Price changed above approved planning allowance')
 ledger=json.loads(a.budget_file.read_text());attempted={r['request_sha256'] for r in ledger['records'].values()};cached={};unavailable={};pending={}
 for key,request in jobs.items():
  f=cache/(key+'.json')
  if f.exists():
   d=json.loads(f.read_text())
   if d['request_sha256']!=key or d.get('request')!=request:raise ValueError('Cache identity mismatch')
   cached[key]=d
  elif key in attempted or list(cache.glob(key+'-raw-*.json')):unavailable[key]='Previously attempted; no retry'
  else:pending[key]=request
 amounts={k:((2*sum(len(m['content'].encode()) for m in v['messages'])+2048)*1e-6+3200*4e-6) for k,v in pending.items()}
 plan={'scope':'Complete the full legacy template-challenge panel; exact original Gemini payload/model/settings and cache keys. Original provider routing remains unconstrained as frozen; current catalog checked, conservative1/4 dollar per million allowance. Shared single-attempt guard replaces retry behavior; no outputs pooled with Qwen.','source_hashes':sources,'code_sha256':digest(__file__),'current_catalog_pricing':prices,'jobs':pending,'cached':list(cached),'previously_unavailable':unavailable,'aliases':aliases,'reservation_usd':sum(amounts.values()),'point_estimate_usd':len(pending)*.001047727052238806,'concurrency':8}
 out=ROOT/'runs/reader-comparison/legacy-remaining-summaries'
 if a.dry_run:print(json.dumps({k:plan[k] for k in ['reservation_usd','point_estimate_usd','concurrency']}|{'pending':len(pending),'cached':len(cached),'unavailable':len(unavailable)}));return
 if out.exists():raise ValueError('Preserve prior run')
 with file_lock(str(a.budget_file)+'.lock'):
  ledger=json.loads(a.budget_file.read_text())
  if not ledger['status'].startswith('paused') or ledger['additional_limit_usd']!=80:raise ValueError('Expected idle80 budget')
  if sum(math.ceil(v*1e6) for v in amounts.values())>80_000_000-ledger['spent_microusd']-ledger['reserved_microusd']:raise ValueError('Whole summary phase reservation does not fit')
  out.mkdir();write_json(out/'registration.json',plan);ledger.update(status='active',active_request_allowlist=list(pending),active_audit_manifest_sha256=fingerprint(plan),audit_scope=plan['scope']);write_json(a.budget_file,ledger)
 def one(k):
  request=pending[k];token=reserve(a.budget_file,amounts[k],k)
  try:
   secret=json.loads(a.credential_file.read_text())['OPENROUTER_API_KEY'];req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(request).encode(),headers={'Authorization':'Bearer '+secret,'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=180) as response:raw=json.load(response)
   write_json(cache/(k+'-raw-'+str(time.time_ns())+'.json'),{'request':request,'response':raw,'budget_reservation':token})
   cost=raw.get('usage',{}).get('cost')
   if cost is None:raise ValueError('Unknown charge')
   settle(a.budget_file,token,float(cost),raw.get('id'))
   if raw.get('model')!=cfg['summarizer_model'] or raw['choices'][0].get('finish_reason')!='stop':raise ValueError('Unavailable model or finish reason')
   judgment=parse_json_reply(raw['choices'][0]['message']['content'])
   if not isinstance(judgment.get('interpretation'),str) or not judgment['interpretation'].strip():raise ValueError('Unavailable interpretation')
   result={'request_sha256':k,'request':request,'requested_model':cfg['summarizer_model'],'resolved_model':raw['model'],'provider':raw.get('provider'),'judgment':judgment,'usage':raw.get('usage'),'response_id':raw.get('id')};write_json(cache/(k+'.json'),result);return k,result,None
  except Exception as e:return k,None,type(e).__name__+': '+str(e)[:150]
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
     try:key,r,err=future.result()
     except Exception as exc:r=None;err=type(exc).__name__+': '+str(exc)[:150];stop=True
     cursor+=1
     if err:unavailable[key]=err;failures+=1
     else:cached[key]=r;failures=0
     if failures>=3:stop=True
     write_json(out/'progress.json',{'attempted':cursor,'total':len(pending),'usable':len(cached),'unavailable':unavailable,'dispatch_stopped':stop})
     if not stop:launch()
   if stop:raise ValueError('Dispatch stopped; active requests drained, receipts retained')
  for panel,rows in aliases.items():
   target=ROOT/f'runs/{panel}-jsummary-test';target.mkdir();summaries=[];errors=[]
   for row in rows:
    if row['key'] in cached:summaries.append({'episode_id':row['episode_id'],'layer':row['layer'],'interpretation':cached[row['key']]['judgment']['interpretation'],'request_sha256':row['key']})
    else:errors.append({'episode_id':row['episode_id'],'layer':row['layer'],'error':unavailable.get(row['key'],'Not attempted')})
   summaries.sort(key=lambda x:(x['episode_id'],x['layer']));write_json(target/'summary-manifest.json',manifests[panel]);write_json(target/'summaries.json',summaries);write_json(target/'summary-complete.json',{'completed':len(summaries),'total':len(rows),'errors':errors,'summaries_sha256':digest(target/'summaries.json'),'manifest_sha256':fingerprint(manifests[panel])})
  write_json(out/'complete.json',{'panels':list(aliases),'usable_unique':len(cached),'unavailable':unavailable,'scope':'Summaries only; reviews and held-out analysis remain required.'})
 finally:
  with file_lock(str(a.budget_file)+'.lock'):
   b=json.loads(a.budget_file.read_text())
   if b['status']=='active':b['status']='paused_after_legacy_summary_stage'
   write_json(a.budget_file,b)
if __name__=='__main__':main()
