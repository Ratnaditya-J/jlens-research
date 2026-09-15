"""Restartable blinded two-reviewer J-view and matched context-only scoring."""
import argparse,concurrent.futures,hashlib,json,os,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2)+'\n');t.replace(p)
def main():
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=12);p.add_argument('--phase',choices=['validation','test'],required=True);p.add_argument('--dataset',choices=['primary','template-challenge','specificity-controls'],default='primary');p.add_argument('--offset',type=int,choices=[0,32,64],default=0);a=p.parse_args();suffix=f'-offset{a.offset}' if a.offset else '';stem={'primary':'fresh','template-challenge':'template-challenge','specificity-controls':'specificity-controls'}[a.dataset];assert a.dataset=='primary' or a.phase=='test'
 if a.phase=='test':
  lockp=ROOT/f'runs/fresh{suffix}-calibration/lock.json';assert lockp.exists(),'Lock calibration before test interpretation'
  lockdata=json.loads(lockp.read_text())
  for name,digest in lockdata['source_hashes'].items():assert sha(ROOT/name)==digest
 if 'OPENAI_API_KEY' not in os.environ:
  credentials=Path('/workspace/private/controller-credentials.json')
  os.environ['OPENAI_API_KEY']=json.loads(credentials.read_text())['OPENAI_API_KEY']
 cfgpath=ROOT/'configs/jview-final-v1.json';cfg=json.loads(cfgpath.read_text());vp=ROOT/f'runs/{stem}{suffix}-assembled/{a.phase}-readouts.json';tp=ROOT/f'runs/{stem}{suffix}-assembled/{a.phase}-contexts.json'
 views=json.loads(vp.read_text());texts={x['episode_id']:x for x in json.loads(tp.read_text())['rows']};out=ROOT/f'runs/{stem}{suffix}-jview-{a.phase}';out.mkdir(parents=True,exist_ok=True)
 import fcntl
 lock=(out/'lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 manifest={'config_sha256':sha(cfgpath),'readouts_sha256':sha(vp),'contexts_sha256':sha(tp),'script_sha256':sha(Path(__file__)),'scope':cfg['scope']}
 m=out/'manifest.json'
 if m.exists():assert json.loads(m.read_text())==manifest,'changed scoring inputs'
 else:write(m,manifest)
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
  req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY'],'Content-Type':'application/json'})
  started=time.time()
  for attempt in range(5):
   try:
    with urllib.request.urlopen(req,timeout=120) as response:raw=json.load(response)
    assert raw['model'] in cfg['required_resolved_models'],'reviewer model identity changed'
    judgment=json.loads(raw['choices'][0]['message']['content']);assert type(judgment['score']) is int and judgment['score'] in [0,1,2];assert judgment['confidence'] in ['high','medium','low']
    for key in ['evidence','rationale','limitations']:assert key in judgment
    break
   except (urllib.error.URLError,TimeoutError,ValueError,AssertionError,KeyError,TypeError) as error:
    if isinstance(error,urllib.error.HTTPError) and error.code not in [429,500,502,503,504]:raise
    if attempt==4:raise
    time.sleep(2**attempt)
  saved={'episode_id':eid,'arm':arm,'requested_model':model,'resolved_model':raw['model'],'request_sha256':digest,'request':payload,'judgment':judgment,'usage':raw.get('usage'),'response_id':raw['id'],'elapsed_seconds':time.time()-started}
  write(path,saved);return saved
 errors=[];completed=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
  futures={pool.submit(review,j):j for j in jobs}
  for future in concurrent.futures.as_completed(futures):
   job=futures[future]
   try:future.result();completed+=1
   except Exception as error:errors.append({'episode_id':job[0],'arm':job[1],'model':job[2],'error_type':type(error).__name__})
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
