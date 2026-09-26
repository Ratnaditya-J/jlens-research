"""Audit successful review results against exact requests, raw replies and spend receipts."""
import argparse
import importlib
import json
import math
from pathlib import Path
from collect_local_readers import valid_score
from contracts import fingerprint, parse_json_reply
from smoke import digest, write_json


def verify_one(job, result, raw, record, candidate, suffix):
    transport=importlib.import_module('budgeted_hosted_'+suffix)
    runner=importlib.import_module('hosted_text_reader_'+suffix)
    expected=transport.payload(candidate,job['system'],job['evidence'])
    key=fingerprint(expected)
    if job['request_id'] != fingerprint({'system':job['system'],'evidence':job['evidence']}):raise ValueError('Changed job')
    if result.get('request_id') != job['request_id'] or result.get('manifest_sha256') != fingerprint(runner.execution_manifest(candidate)):
        raise ValueError('Result execution mismatch')
    if raw.get('request') != expected or result.get('api_request_sha256') != key:raise ValueError('Request mismatch')
    response=raw['response'];config=transport.CONFIGS[candidate]
    if result.get('raw_response') != response:raise ValueError('Raw response mismatch')
    if response.get('model') not in config['response_models'] or response.get('provider') != config['provider']:raise ValueError('Wrong response model/provider')
    choice=response['choices'][0]
    if choice.get('finish_reason') != 'stop':raise ValueError('Incomplete response')
    if result.get('judgment') != parse_json_reply(choice['message']['content']) or valid_score(result) is None:raise ValueError('Invalid or altered score')
    cost=response.get('usage',{}).get('cost')
    if not isinstance(cost,(float,int)) or not math.isfinite(cost) or cost < 0:raise ValueError('Missing valid cost')
    if record.get('request_sha256') != key or record.get('status') != 'settled' or record.get('response_id') != response['id'] or record.get('actual_microusd') != math.ceil(float(cost)*1e6):
        raise ValueError('Settlement mismatch')
    return record['actual_microusd']


def audit(jobs_path, reader, budget_file, candidate, suffix):
    jobs=json.loads(jobs_path.read_text())['jobs']
    ledger=json.loads(budget_file.read_text())
    sources={str(jobs_path):digest(jobs_path),str(reader/'manifest.json'):digest(reader/'manifest.json')}
    runner=importlib.import_module('hosted_text_reader_'+suffix)
    if json.loads((reader/'manifest.json').read_text()) != runner.execution_manifest(candidate):raise ValueError('Reader manifest changed')
    completion=reader/(jobs_path.stem+'-complete.json')
    complete=json.loads(completion.read_text())
    if complete != {'jobs_sha256':digest(jobs_path),'manifest_sha256':fingerprint(runner.execution_manifest(candidate)),'unique_requests':len(jobs)}:raise ValueError('Incomplete cohort')
    sources[str(completion)]=digest(completion)
    cost=0;tokens=set()
    for job in jobs:
        path=reader/'results'/(job['request_id']+'.json');result=json.loads(path.read_text())
        if result.get('status') != 'ok':raise ValueError('Unavailable review retained; cohort not fully verified')
        raws=list((reader/'api-cache').glob(result['api_request_sha256']+'-raw-*.json'))
        if len(raws)!=1:raise ValueError('Expected exactly one raw receipt; no retry')
        raw=json.loads(raws[0].read_text());token=raw['budget_reservation']
        if token in tokens:raise ValueError('Duplicate settlement')
        tokens.add(token)
        cost+=verify_one(job,result,raw,ledger['records'][token],candidate,suffix)
        for source in [path,raws[0]]:sources[str(source)]=digest(source)
    return {'candidate':candidate,'passed':True,'verified_reviews':len(jobs),'settled_microusd':cost,'source_hashes':sources,'ledger_snapshot_sha256':digest(budget_file),'verifier_sha256':digest(__file__),'scope':'Execution, output schema and receipt integrity only. No semantic faithfulness, independent accuracy or detector performance claim.'}


def main():
    p=argparse.ArgumentParser()
    for name in ['jobs','reader','budget-file','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate',choices=['gpt41reference','gpt54lowreference'],required=True);a=p.parse_args()
    report=audit(a.jobs,a.reader,a.budget_file,a.candidate,'reference' if a.candidate=='gpt41reference' else 'lowreference')
    write_json(a.out,report);print(json.dumps({k:v for k,v in report.items() if k!='source_hashes'}))


if __name__=='__main__':main()
