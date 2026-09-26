"""Explicit third audit allocation within the existing $10 project ceiling.

This is a separately registered decision, not an automatic budget escalator.
Only the fixed frontier pair qualification phase is eligible. Historical charges remain.
"""
import json
import math
import time
from budgeted_api_client import file_lock
from contracts import fingerprint
from smoke import write_json


def activate_frontier_pair(path, plan):
    if plan.get('kind') != 'bounded-hosted-frontier-pair-qualification-v1' or plan.get('cumulative_limit_usd') != 5:
        raise ValueError('Unregistered third audit phase')
    keys=plan['request_allowlist']
    if len(keys)!=144 or len(set(keys))!=144:
        raise ValueError('Exactly144 unique qualification requests required')
    with file_lock(str(path)+'.lock'):
        ledger=json.loads(path.read_text())
        if not ledger['status'].startswith('paused'):
            raise ValueError('Prior coordinator must finish before the registered budget revision')
        old=ledger['additional_limit_usd']
        if old!=2:
            raise ValueError('Unexpected previous audit ceiling')
        held=ledger.get('reserved_microusd',0)
        if held!=sum(x['reserved_microusd'] for x in ledger['records'].values() if x['status']=='reserved'):
            raise ValueError('Uncertain charge accounting differs')
        if any(x['request_sha256'] in keys for x in ledger['records'].values()):
            raise ValueError('Qualification already attempted; no retries')
        spent=ledger.get('spent_microusd',0)
        if plan['maximum_reserved_microusd']>5_000_000-spent-held:
            raise ValueError('Full registered batch exceeds the third audit allowance')
        ledger.setdefault('budget_amendments',[]).append({'at':time.time(),
            'previous_limit_usd':old,'new_limit_usd':5,'plan_sha256':fingerprint(plan),
            'reason':'Deliberately registered144-request frontier pair qualification after failed reader candidates; within existing$10 project ceiling. No production/test inference.'})
        ledger.update(status='active',additional_limit_usd=5,
            active_request_allowlist=keys,active_audit_manifest_sha256=fingerprint(plan),
            audit_scope=plan['scope'],carried_uncertain_microusd_at_activation=held)
        write_json(path,ledger)
