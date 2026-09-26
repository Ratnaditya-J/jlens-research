"""Distinct GPT-5.4 low-reasoning reference-family transport; reuses the existing spend ledger guard."""
import json
import hashlib
import urllib.error
import time
import urllib.request
from pathlib import Path

from budgeted_api_client import file_lock, reserve, settle, lowcost_reservation
from contracts import fingerprint, parse_json_reply
from literal_evidence import literal_json
from smoke import write_json

CONFIGS = {
 'gpt54lowreference': {'repo':'openai/gpt-5.4','family':'gpt5','endpoint':'openai/flex','provider':'OpenAI',
  'prompt_price':1.25,'completion_price':7.5,'reserved_output_tokens':2048,
  'response_models':['openai/gpt-5.4','openai/gpt-5.4-2026-03-05','openai/gpt-5.4-20260305']},
}


def payload(candidate, system, evidence):
    c=CONFIGS[candidate]
    return {'model':c['repo'],'messages':[{'role':'system','content':system},{'role':'user','content':literal_json(evidence)}],
      'max_tokens':1600,'reasoning':{'effort':'low'},'response_format':{'type':'json_object'},
      'provider':{'only':[c['endpoint']],'order':[c['endpoint']],'allow_fallbacks':False,'require_parameters':True,
       'max_price':{'prompt':c['prompt_price'],'completion':c['completion_price']}}}


def reservation(candidate, request):
    c=CONFIGS[candidate];n=sum(len(m['content'].encode('utf-8')) for m in request['messages'])
    return ((2*n+2048)*c['prompt_price']+c['reserved_output_tokens']*c['completion_price'])/1e6


def request_json(candidate, system, evidence, cache, credential_file, *, budget_file):
    CONFIG=CONFIGS[candidate]
    request = payload(candidate, system, evidence)
    key = fingerprint(request)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache/(key+'.json')
    with file_lock(cache/(key+'.lock')):
        if path.exists():
            result = json.loads(path.read_text())
            if result['request_sha256'] != key or result['requested_model'] != CONFIG['repo']:
                raise ValueError('Changed GPT-5.4 low-reasoning reference-family cache identity')
            return result
        with file_lock(str(budget_file)+'.lock'):
            ledger = json.loads(Path(budget_file).read_text())
            if key not in ledger.get('active_request_allowlist', []):
                raise RuntimeError('Unregistered GPT-5.4 low-reasoning reference-family request')
        token = reserve(budget_file, reservation(candidate, request), key)
        credential = json.loads(Path(credential_file).read_text())['OPENROUTER_API_KEY']
        req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                data=json.dumps(request).encode(),
                headers={'Authorization': 'Bearer '+credential, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                raw = json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read(65536)
            write_json(cache/(key+'-http-error.json'), {'status_code': exc.code, 'body_prefix_sha256': hashlib.sha256(body).hexdigest(), 'budget_reservation': token, 'scope': 'Error diagnostic only; full reservation retained and no retry.'})
            # Pause the batch on its first HTTP failure; never dispatch the rest.
            with file_lock(str(budget_file)+'.lock'):
                ledger=json.loads(Path(budget_file).read_text())
                ledger['status']='paused_http_error'
                ledger['http_failure']={'status_code':exc.code,'request_sha256':key}
                write_json(budget_file,ledger)
            raise
        write_json(cache/(key+'-raw-'+str(time.time_ns())+'.json'),
                   {'request': request, 'response': raw, 'budget_reservation': token})
        cost = raw.get('usage', {}).get('cost')
        if cost is None:
            raise RuntimeError('Unknown charge; reservation retained')
        settle(budget_file, token, float(cost), raw.get('id'))
        if raw.get('model') not in CONFIG['response_models'] or raw.get('provider') != CONFIG['provider']:
            raise ValueError('Resolved model or provider differs from registered execution')
        if raw['choices'][0].get('finish_reason') != 'stop':
            raise ValueError('Non-stop finish reason')
        judgment = parse_json_reply(raw['choices'][0]['message']['content'])
        result = {'request_sha256': key, 'requested_model': CONFIG['repo'], 'judgment': judgment,
                  'raw_response': raw, 'budget_reservation': token}
        write_json(path, result)
        return result
