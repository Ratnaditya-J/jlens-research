"""Completion-triggered frozen evaluation; two concurrent offline endpoint workers."""
import argparse,json,os,subprocess,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from parallel_heldout_reviews import CANDIDATES, verify_review
from smoke import digest,write_json

def main():
    p=argparse.ArgumentParser()
    for n in ['review-run','plan','budget-file','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--wait-pid',type=int,required=True);a=p.parse_args()
    cp=a.review_run/'complete.json';deadline=time.monotonic()+14400
    while not cp.exists():
        if time.monotonic()>deadline:raise TimeoutError('Review wait timed out; no restart')
        try:os.kill(a.wait_pid,0)
        except ProcessLookupError:raise RuntimeError('Review run stopped without complete accounting')
        time.sleep(1)
    done=json.loads(cp.read_text());registration=json.loads((a.review_run/'registration.json').read_text())
    for path,sha in done['source_hashes'].items():
        if digest(path)!=sha:raise ValueError('Review source changed')
    ledger=json.loads(a.budget_file.read_text())
    for c,s in CANDIDATES.items():
        reader=a.review_run/c
        if registration['costs'][c]['cached']!=0:raise ValueError('This handoff expects the registered zero-cache cohort')
        jobs=registration['pending'][c]
        if len(list((reader/'results').glob('*.json')))!=len(jobs):raise ValueError('Incomplete review cohort')
        for j in jobs:
            result=json.loads((reader/'results'/(j['request_id']+'.json')).read_text())
            verify_review(j,result,[reader],c,s,ledger)
    if a.out.exists():raise ValueError('Preserve prior evaluation handoff')
    a.out.mkdir(parents=True);plan=json.loads(a.plan.read_text())
    def run(row):
        if digest(row['lock'])!=row['lock_sha256']:raise ValueError('Frozen threshold lock changed')
        for stage in ['collection','evaluation']:
            with (a.out/(row['endpoint']+'-'+stage+'.log')).open('w') as log:
                subprocess.run(row[stage],stdout=log,stderr=subprocess.STDOUT,check=True)
        return row['endpoint']
    with ThreadPoolExecutor(max_workers=2) as pool:completed=list(pool.map(run,plan['plans']))
    write_json(a.out/'complete.json',{'endpoints':completed,'plan_sha256':digest(a.plan),'review_completion_sha256':digest(cp)})
    print(json.dumps({'evaluated':completed}),flush=True)

if __name__=='__main__':main()
