"""Content-addressed, auditable local API transport. Never runs on GPU workers."""
import json,time,urllib.request,urllib.error,threading
from pathlib import Path
from contracts import fingerprint,parse_json_reply
from smoke import write_json
_locks={};_guard=threading.Lock()

def request_json(model,system,evidence,cache,credential_file,max_tokens=1600):
 payload={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(evidence,ensure_ascii=False)}],'response_format':{'type':'json_object'},'max_tokens':max_tokens,'provider':{'require_parameters':True}}
 if model.startswith('openai/gpt-5'):payload['reasoning']={'effort':'low'}
 else:payload['temperature']=0
 keyhash=fingerprint(payload);path=Path(cache)/(keyhash+'.json')
 with _guard:lock=_locks.setdefault(keyhash,threading.Lock())
 with lock:
  if path.exists():
   result=json.loads(path.read_text())
   if result['request_sha256']!=keyhash or result['requested_model']!=model:raise ValueError('API cache mismatch')
   return result
  key=json.loads(Path(credential_file).read_text())['OPENROUTER_API_KEY']
  req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
  for attempt in range(5):
   try:
    with urllib.request.urlopen(req,timeout=180) as response:raw=json.load(response)
    break
   except (urllib.error.URLError,TimeoutError) as error:
    if isinstance(error,urllib.error.HTTPError) and error.code not in [429,500,502,503,504]:raise RuntimeError(f'API HTTP {error.code}') from None
    if attempt==4:raise RuntimeError('API retries exhausted') from None
    time.sleep(2**attempt)
  write_json(Path(cache)/(keyhash+'-raw.json'),{'request':payload,'response':raw})
  if raw.get('model')!=model:raise ValueError('Resolved model changed')
  choice=raw['choices'][0]
  if choice.get('finish_reason')!='stop':raise ValueError('Incomplete API response')
  judgment=parse_json_reply(choice['message']['content'])
  result={'request_sha256':keyhash,'request':payload,'requested_model':model,'resolved_model':raw['model'],'provider':raw.get('provider'),'judgment':judgment,'usage':raw.get('usage'),'response_id':raw.get('id')}
  write_json(path,result);return result
