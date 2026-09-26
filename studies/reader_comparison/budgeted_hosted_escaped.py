"""Separate frozen DeepSeek escaped-output transport; reuses the existing spend ledger guard."""
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

from budgeted_api_client import LOW_COST_CANDIDATES, lowcost_payload
CONFIG = dict(LOW_COST_CANDIDATES['deepseek32'])
OUTPUT_RULE = r"""Transport formatting requirement: Return exactly the requested JSON object. In every generated text field, encode any less-than or greater-than character using JSON Unicode escapes \u003c and \u003e. Do not write literal angle-bracket delimiters anywhere in your output or reasoning. When discussing markup during reasoning, use words such as opening think tag or closing think tag. Preserve the original scoring rubric and evidence meanings; this rule changes serialization only."""


def payload(system, evidence):
    return lowcost_payload('deepseek32', system + '\n\n' + OUTPUT_RULE, evidence)


def reservation(request):
    # Planning allowance, not a provider-enforced token or invoice cap.
    # Reserve 8192 total output tokens, twice the preceding audit allowance.
    byte_count = sum(len(m['content'].encode('utf-8')) for m in request['messages'])
    price = request['provider']['max_price']
    return ((2*byte_count+2048)*price['prompt'] + 8192*price['completion'])/1e6


def parse_output(content):
    if '<' in content or '>' in content:
        raise ValueError('Output delimiter serialization requirement violated')
    return parse_json_reply(content)


def request_json(candidate, system, evidence, cache, credential_file, *, budget_file):
    if candidate != 'deepseek32escaped':
        raise ValueError('Unregistered escaped-output reader')
    request = payload(system, evidence)
    key = fingerprint(request)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache/(key+'.json')
    with file_lock(cache/(key+'.lock')):
        if path.exists():
            result = json.loads(path.read_text())
            if result['request_sha256'] != key or result['requested_model'] != CONFIG['repo']:
                raise ValueError('Changed escaped-output cache identity')
            return result
        with file_lock(str(budget_file)+'.lock'):
            ledger = json.loads(Path(budget_file).read_text())
            if key not in ledger.get('active_request_allowlist', []):
                raise RuntimeError('Unregistered escaped-output request')
        token = reserve(budget_file, reservation(request), key)
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
        judgment = parse_output(raw['choices'][0]['message']['content'])
        result = {'request_sha256': key, 'requested_model': CONFIG['repo'], 'judgment': judgment,
                  'raw_response': raw, 'budget_reservation': token}
        write_json(path, result)
        return result
