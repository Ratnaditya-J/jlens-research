"""Fail-closed, single-attempt API transport for small post-amendment audits.

Provider price ceilings: https://openrouter.ai/blog/tutorials/how-to-get-the-lowest-cost-llm-inference-on-openrouter/
No automatic retries. Uncertain calls retain their complete cost reservation.
Frozen legacy API transport is intentionally unchanged.
"""
import contextlib,fcntl,json,math,time,uuid,urllib.request
from pathlib import Path
from contracts import fingerprint,parse_json_reply
from smoke import write_json

@contextlib.contextmanager
def file_lock(path):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a+') as handle:
  fcntl.flock(handle,fcntl.LOCK_EX)
  try:yield
  finally:fcntl.flock(handle,fcntl.LOCK_UN)

def reserve(path,amount_usd,request_sha):
 path=Path(path);amount=math.ceil(amount_usd*1_000_000)
 if not math.isfinite(amount_usd) or amount<=0:raise ValueError('Invalid cost reservation')
 with file_lock(str(path)+'.lock'):
  ledger=json.loads(path.read_text())
  if ledger['status']!='active':raise RuntimeError('OpenRouter inference is paused by the project cost policy')
  spent=ledger.get('spent_microusd',0);held=ledger.get('reserved_microusd',0);limit=math.floor(ledger['additional_limit_usd']*1_000_000)
  if spent+held+amount>limit:raise RuntimeError('Additional OpenRouter budget exhausted; use local inference')
  token=uuid.uuid4().hex;ledger['reserved_microusd']=held+amount;ledger['records'][token]={'request_sha256':request_sha,'reserved_microusd':amount,'status':'reserved','at':time.time()};write_json(path,ledger)
 return token

def settle(path,token,cost_usd,response_id):
 path=Path(path);actual=math.ceil(cost_usd*1_000_000)
 if not math.isfinite(cost_usd) or actual<0:raise ValueError('Invalid reported charge')
 with file_lock(str(path)+'.lock'):
  ledger=json.loads(path.read_text());record=ledger['records'][token]
  if record['status']!='reserved':raise ValueError('Reservation already settled')
  held=record['reserved_microusd'];ledger['reserved_microusd']-=held;ledger['spent_microusd']=ledger.get('spent_microusd',0)+actual;record.update(status='settled',actual_microusd=actual,response_id=response_id)
  if actual>held:ledger['status']='paused_unexpected_charge'
  write_json(path,ledger)
  if actual>held:raise RuntimeError('Provider charge exceeded the conservative reservation; inference paused')

def request_json(model,system,evidence,cache,credential_file,*,budget_file,max_tokens=1600):
 if not 16<=max_tokens<=1600:raise ValueError('Audit output budget must be16..1600 tokens')
 payload={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(evidence,ensure_ascii=False)}],'response_format':{'type':'json_object'},'max_tokens':max_tokens,'provider':{'require_parameters':True}}
 if model.startswith('openai/gpt-5'):payload['reasoning']={'effort':'low'}
 else:payload['temperature']=0
 legacy=fingerprint(payload);cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
 # Exact prior requests cost nothing and retain their original provenance.
 prior=cache/(legacy+'.json')
 if prior.exists():
  result=json.loads(prior.read_text())
  if result['request_sha256']!=legacy or result['requested_model']!=model:raise ValueError('Invalid legacy cache entry')
  return result
 if model!='google/gemini-3.8-flash':raise RuntimeError('Premium uncached models disabled by cost amendment')
 payload['provider']['max_price']={'prompt':1,'completion':4}
 key=fingerprint(payload);path=cache/(key+'.json')
 with file_lock(cache/(key+'.lock')):
  if path.exists():return json.loads(path.read_text())
  # A deliberately loose byte-based upper bound plus chat-framing allowance;
  # doubled output allowance also reserves for reasoning-token accounting.
  byte_count=sum(len(m['content'].encode('utf-8')) for m in payload['messages'])
  maximum=(2*byte_count+2048)/1_000_000+2*max_tokens*4/1_000_000
  token=reserve(budget_file,maximum,key)
  credential=json.loads(Path(credential_file).read_text())['OPENROUTER_API_KEY']
  req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+credential,'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=180) as response:raw=json.load(response)
  write_json(cache/(key+'-raw-'+str(time.time_ns())+'.json'),{'request':payload,'response':raw,'budget_reservation':token})
  cost=raw.get('usage',{}).get('cost')
  if cost is None:raise RuntimeError('Unknown provider charge; reservation retained')
  settle(budget_file,token,float(cost),raw.get('id'))
  if raw.get('model')!=model:raise ValueError('Resolved model changed')
  judgment=parse_json_reply(raw['choices'][0]['message']['content'])
  result={'request_sha256':key,'requested_model':model,'judgment':judgment,'raw_response':raw,'budget_reservation':token};write_json(path,result);return result
