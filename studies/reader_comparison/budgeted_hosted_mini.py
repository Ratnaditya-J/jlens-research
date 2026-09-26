"""Separate frozen GPT-5.4 mini Flex transport; reuses the existing spend ledger guard."""
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

CONFIG = {'repo': 'openai/gpt-5.4-mini', 'family': 'gpt5',
          'endpoint': 'openai/flex', 'provider': 'OpenAI', 'ignored_endpoints': [],
          'prompt_price': .375, 'completion_price': 2.25,
          'response_models': ['openai/gpt-5.4-mini', 'openai/gpt-5.4-mini-20260317', 'openai/gpt-5.4-mini-2026-03-17']}


def payload(system, evidence):
    return {'model': CONFIG['repo'],
            'messages': [{'role': 'system', 'content': system},
                         {'role': 'user', 'content': literal_json(evidence)}],
            'seed': 20260926, 'max_tokens': 2048, 'reasoning': {'effort': 'medium'},
            'response_format': {'type': 'json_object'},
            'provider': {'only': [CONFIG['endpoint']], 'order': [CONFIG['endpoint']],
                         'allow_fallbacks': False, 'require_parameters': True,
                         'ignore': CONFIG['ignored_endpoints'],
                         'max_price': {'prompt': CONFIG['prompt_price'], 'completion': CONFIG['completion_price']}}}


def request_json(candidate, system, evidence, cache, credential_file, *, budget_file):
    if candidate != 'gpt54miniflex':
        raise ValueError('Unregistered mini Flex reader')
    request = payload(system, evidence)
    key = fingerprint(request)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache/(key+'.json')
    with file_lock(cache/(key+'.lock')):
        if path.exists():
            result = json.loads(path.read_text())
            if result['request_sha256'] != key or result['requested_model'] != CONFIG['repo']:
                raise ValueError('Changed mini Flex cache identity')
            return result
        with file_lock(str(budget_file)+'.lock'):
            ledger = json.loads(Path(budget_file).read_text())
            if key not in ledger.get('active_request_allowlist', []):
                raise RuntimeError('Unregistered mini Flex request')
        token = reserve(budget_file, lowcost_reservation(request), key)
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
