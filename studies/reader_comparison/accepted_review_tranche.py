"""Bounded first validation review tranche; exact accepted executions and cache reuse."""
import argparse
import importlib
import json
import math
import shutil
from pathlib import Path
from audit_budgeted_reader import pause_budget
from budgeted_api_client import file_lock
from collect_local_readers import load_jobs, load_results, valid_score
from contracts import fingerprint
from smoke import digest, write_json
from verify_reader_acceptance import load_acceptance

JOBS_SHA = '93c9c60968be164d27fa85477a4d65ecb5d9f5a26686b5089387a43733798c82'
KIND = 'accepted-primary-validation-review-first64-v1'
CANDIDATES = [('gpt41reference', 'reference'), ('gpt54lowreference', 'lowreference')]


def activate(path, plan):
    keys = plan['request_allowlist']
    if plan.get('kind') != KIND or plan.get('jobs_sha256') != JOBS_SHA or len(keys) != 64 or len(set(keys)) != 64:
        raise ValueError('Only registered first64 validation reviews allowed')
    with file_lock(str(path)+'.lock'):
        ledger = json.loads(path.read_text())
        if not ledger['status'].startswith('paused') or ledger['additional_limit_usd'] != 5:
            raise ValueError('Paused existing$5 allowance required')
        held = ledger.get('reserved_microusd', 0)
        if held != sum(r['reserved_microusd'] for r in ledger['records'].values() if r['status'] == 'reserved'):
            raise ValueError('Uncertain accounting differs')
        if any(r['request_sha256'] in keys for r in ledger['records'].values()):
            raise ValueError('Previously attempted request; no retry')
        if not 0 < plan['maximum_reserved_microusd'] <= 5_000_000-ledger.get('spent_microusd', 0)-held:
            raise ValueError('Entire tranche must fit unchanged allowance')
        ledger.update(status='active', active_request_allowlist=keys,
                      active_audit_manifest_sha256=fingerprint(plan), audit_scope=plan['scope'],
                      carried_uncertain_microusd_at_activation=held)
        write_json(path, ledger)


def prepare(jobs_dir, budget_file):
    m, jobs, aliases = load_jobs(jobs_dir)
    if m['phase'] != 'validation' or m['stage'] != 'reviews' or m['endpoint'] != 'before_action' or digest(jobs_dir/'jobs.json') != JOBS_SHA:
        raise ValueError('Only frozen primary validation reviews allowed')
    ledger = json.loads(budget_file.read_text())
    attempted = {r['request_sha256'] for r in ledger['records'].values()}
    selections, reused, sources, keys, maximum = {}, {}, {}, [], 0
    for candidate, suffix in CANDIDATES:
        transport = importlib.import_module('budgeted_hosted_'+suffix)
        runner = importlib.import_module('hosted_text_reader_'+suffix)
        acceptance = Path('studies/reader_comparison/evidence')/('hosted-'+candidate+'-acceptance'+('-v2' if suffix == 'reference' else '')+'.json')
        sources.update(load_acceptance(acceptance, runner.execution_manifest(candidate)))
        coverage = Path('runs/reader-comparison')/('hosted-'+candidate+'-coverage')/'reader'
        manifest, results = load_results(coverage, jobs)
        if manifest != runner.execution_manifest(candidate):raise ValueError('Changed coverage execution')
        reuse, fresh = [], []
        for job in sorted(jobs, key=lambda x:x['request_id']):
            request = transport.payload(candidate, job['system'], job['evidence'])
            key = fingerprint(request)
            if key in attempted:
                result = results.get(job['request_id'])
                if valid_score(result) is None or result.get('api_request_sha256') != key:
                    raise ValueError('Attempted request lacks accepted reusable result')
                path = coverage/'results'/(job['request_id']+'.json')
                if sources.get(str(path.resolve())) != digest(path):
                    raise ValueError('Cached result not covered by acceptance provenance')
                reuse.append(str(path))
            elif len(fresh) < 32:
                fresh.append(job);keys.append(key)
                maximum += math.ceil(transport.reservation(candidate, request)*1e6)
        if len(fresh) != 32 or len(reuse) != 18:raise ValueError('Unexpected first-tranche cohort')
        selections[candidate] = fresh;reused[candidate] = reuse
    plan = {'kind':KIND, 'jobs_sha256':JOBS_SHA, 'request_allowlist':sorted(keys),
            'maximum_reserved_microusd':maximum, 'acceptance_source_hashes':sources,
            'new_jobs':selections, 'reused_results':reused, 'code_sha256':digest(__file__),
            'scope':'First32 unattempted jobs sorted by content hash per accepted judge, plus18 exact accepted coverage-cache results each. Primary pre-action validation only; all nine arms remain in full cohort. No retries, fallback, held-out evaluation, calibration lock or cap increase.'}
    return plan


def main():
    p = argparse.ArgumentParser()
    for name in ['jobs','budget-file','credential-file','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    plan = prepare(a.jobs, a.budget_file)
    if a.dry_run:
        print(json.dumps({k:v for k,v in plan.items() if k not in ['acceptance_source_hashes','new_jobs','reused_results','request_allowlist']},indent=2));return
    if a.out.exists():raise ValueError('Preserve prior tranche; no automatic restart')
    a.out.mkdir(parents=True);write_json(a.out/'plan.json',plan)
    for candidate,suffix in CANDIDATES:
        root=a.out/candidate;root.mkdir();(root/'results').mkdir()
        for source in plan['reused_results'][candidate]:shutil.copyfile(source,root/'results'/Path(source).name)
        write_json(a.out/(candidate+'-jobs.json'),{'jobs':plan['new_jobs'][candidate]})
    activate(a.budget_file,plan)
    try:
        for candidate,suffix in CANDIDATES:
            if json.loads(a.budget_file.read_text())['status'] != 'active':break
            importlib.import_module('hosted_text_reader_'+suffix).run_jobs(candidate,a.out/(candidate+'-jobs.json'),a.out/candidate,a.credential_file,a.budget_file)
    finally:
        ledger=pause_budget(a.budget_file)
        write_json(a.out/'cost.json',{k:ledger.get(k) for k in ['spent_microusd','reserved_microusd','status']})


if __name__ == '__main__':main()
