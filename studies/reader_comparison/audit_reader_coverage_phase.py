"""Coverage budget guard for the registered single-worker candidates; never raises the cap."""
import json
import math
from budgeted_api_client import file_lock
from contracts import fingerprint
from smoke import write_json


def activate_coverage_budget(path, plan):
    """Keep prior uncertain charges fully reserved; never retry their requests."""
    if plan.get('kind') != 'bounded-hosted-registered-reader-coverage-v1':
        raise ValueError('Unregistered coverage phase')
    if len(plan['request_allowlist']) != 90 or len(set(plan['request_allowlist'])) != 90:
        raise ValueError('Exactly90 unique coverage requests required')
    if plan.get('jobs_sha256') != 'ca9bc458bfc298a2c649c5de0e4bd0288fbe85c78de6a63f13bd88cbf7d8c441':
        raise ValueError('Coverage cohort changed')
    with file_lock(str(path)+'.lock'):
        ledger = json.loads(path.read_text())
        if not ledger['status'].startswith('paused'):
            raise ValueError('Previous coordinator must be finished and ledger paused')
        if ledger['additional_limit_usd'] != 5:
            raise ValueError('Coverage cannot raise the existing $5 ceiling')
        if any(record['request_sha256'] in plan['request_allowlist'] for record in ledger['records'].values()):
            raise ValueError('Coverage request already attempted; no retry')
        held = ledger.get('reserved_microusd', 0)
        if held != sum(record['reserved_microusd'] for record in ledger['records'].values() if record['status'] == 'reserved'):
            raise ValueError('Uncertain reservation ledger is inconsistent')
        remaining = math.floor(ledger['additional_limit_usd']*1e6)-ledger.get('spent_microusd', 0)-held
        if plan['maximum_reserved_microusd'] > remaining:
            raise ValueError('All coverage reservations must fit after carrying prior uncertain charges')
        ledger.update(status='active', active_request_allowlist=plan['request_allowlist'],
                      active_audit_manifest_sha256=fingerprint(plan), audit_scope=plan['scope'],
                      carried_uncertain_microusd_at_activation=held)
        write_json(path, ledger)
