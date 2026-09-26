"""One registered144-request frontier/alternate-route qualification audit."""
import argparse
import json
import math
import shutil
import time
from pathlib import Path

from audit_budgeted_reader import fixture_jobs, pause_budget
from budgeted_hosted_frontier_pair import payload as lowcost_payload, reservation
from contracts import fingerprint
from hosted_text_reader_frontier_pair import execution_manifest, run_jobs
from smoke import digest, write_json


from audit_frontier_pair_phase import activate_frontier_pair as activate_budget


def main():
    p = argparse.ArgumentParser()
    for name in ['bridge', 'policy', 'credential-file', 'budget-file', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    groups = [('bridge', a.bridge, fixture_jobs(a.bridge, 48), 'local-bridge-jobs'),
              ('policy', a.policy, fixture_jobs(a.policy, 24), 'local-policy-check-jobs')]
    candidates = ['gpt54flex', 'deepseek32atlas']
    payloads = [lowcost_payload(c, j['system'], j['evidence'])
                for c in candidates for _, _, jobs, _ in groups for j in jobs]
    keys = [fingerprint(p) for p in payloads]
    if len(keys) != 144 or len(set(keys)) != 144:
        raise ValueError('Unexpected qualification cohort or duplicate API request')
    plan = {'kind': 'bounded-hosted-frontier-pair-qualification-v1', 'cumulative_limit_usd': 5,
            'readers': {c: execution_manifest(c) for c in candidates},
            'fixture_protocol_sha256': {n: digest(d/'protocol.json') for n, d, _, _ in groups},
            'request_allowlist': sorted(keys),
            'maximum_reserved_microusd': sum(math.ceil(reservation(c, lowcost_payload(c,j['system'],j['evidence']))*1e6) for c in candidates for _,_,jobs,_ in groups for j in jobs),
            'code_sha256': digest(__file__),
            'activation_guard_sha256': digest(Path(__file__).with_name('audit_frontier_pair_phase.py')),
            'fixture_loader_code_sha256': digest(Path(__file__).with_name('audit_budgeted_reader.py')),
            'scope': 'Two adaptive qualification candidates after failed local executions; same 48+24 fixtures and original gates. No held-out inference. Explicit cumulative$5 audit allocation within the$10 project ceiling; no retry or production adoption. GPT-5.4 is one source reference model, so its bridge agreement is not an independent accuracy estimate. AtlasCloud preserves FP8 but changes serving execution; all gates must be repeated.'}
    if a.dry_run:
        print(json.dumps(plan, indent=2))
        return
    if a.out.exists():
        raise ValueError('Preserve existing audit directory; no automatic rerun')
    a.out.mkdir(parents=True)
    write_json(a.out/'audit-plan.json', plan)
    inputs = a.out/'inputs'
    inputs.mkdir()
    for _, directory, _, stem in groups:
        shutil.copyfile(directory/'jobs.json', inputs/(stem+'.json'))
    activate_budget(a.budget_file, plan)
    try:
        for candidate in candidates:
            for _, _, _, stem in groups:
                run_jobs(candidate, inputs/(stem+'.json'), a.out/candidate,
                         a.credential_file, a.budget_file)
    finally:
        ledger = pause_budget(a.budget_file)
        write_json(a.out/'cost.json', {'cumulative_limit_usd': ledger['additional_limit_usd'],
                   'cumulative_spent_usd': ledger.get('spent_microusd', 0)/1e6,
                   'reserved_uncertain_usd': ledger.get('reserved_microusd', 0)/1e6,
                   'ledger_status': ledger['status'], 'ledger_sha256': digest(a.budget_file),
                   'ended_at': time.time()})


if __name__ == '__main__':
    main()
