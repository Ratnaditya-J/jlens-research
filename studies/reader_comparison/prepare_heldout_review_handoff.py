"""Immediate, offline summary-to-review handoff; no API calls or test scoring."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from smoke import digest, write_json

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--summary-run',type=Path,required=True)
    p.add_argument('--wait-pid',type=int,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('Preserve prior handoff evidence')
    deadline=time.monotonic()+7200
    cp=a.summary_run/'complete.json'
    while not cp.exists():
        if time.monotonic()>deadline:raise TimeoutError('Summary handoff deadline; no restart')
        try:os.kill(a.wait_pid,0)
        except ProcessLookupError:raise RuntimeError('Summary producer exited without completion; investigate existing output')
        time.sleep(1)
    done=json.loads(cp.read_text())
    if done['requests']!=588 or done['usable']+len(done['missing'])!=588:
        raise ValueError('Expected full held-out summary accounting')
    for path,sha in done['source_hashes'].items():
        if digest(path)!=sha:raise ValueError('Summary provenance changed')
    a.out.mkdir(parents=True)
    commands=[];endpoints={};root=Path('runs/reader-comparison')
    for e in ['during_action','after_action','before_action_32','before_action_64']:
        prefix='standard' if e in ['during_action','after_action'] else 'accepted'
        jobdir=root/(prefix+'-test-summaries-'+e)
        target=root/(prefix+'-test-'+e);target.mkdir(parents=True,exist_ok=True)
        summary=target/'summaries.json'
        if summary.exists() or (target/'reviews').exists():raise ValueError('Refuse to replace prepared test artifacts')
        collect=[sys.executable,'studies/reader_comparison/collect_local_readers.py',
                 '--jobs',str(jobdir),'--readers',str(a.summary_run/'reader'),
                 '--second-reader-family','gpt5','--reader-acceptances',
                 'studies/reader_comparison/evidence/hosted-gpt54lowreference-acceptance.json',
                 '--out',str(summary)]
        prepare=[sys.executable,'studies/reader_comparison/local_reader_jobs.py',
                 '--bundle',str(root/('bundle-'+e+'.json')),'--phase','test','--stage','reviews',
                 '--summaries',str(summary),'--lock',str(root/(prefix+'-calibration-'+e)/'lock.json'),
                 '--out',str(target/'reviews')]
        for cmd in [collect,prepare]:
            subprocess.run(cmd,check=True);commands.append(cmd)
        jobs=json.loads((target/'reviews/jobs.json').read_text())['jobs']
        aliases=json.loads((target/'reviews/aliases.json').read_text())
        endpoints[e]={'jobs':str(target/'reviews'),'unique_requests':len(jobs),
                      'missing_review_aliases':sum(x['request_id'] is None for x in aliases),
                      'total_aliases':len(aliases),'episodes':len({x['episode_id'] for x in aliases}),
                      'jobs_sha256':digest(target/'reviews/jobs.json'),
                      'summaries_sha256':digest(summary)}
    write_json(a.out/'complete.json',{'endpoints':endpoints,'commands':commands,
        'summary_completion_sha256':digest(cp),'code_sha256':digest(__file__),
        'scope':'Offline automatic handoff after full summary accounting. Missing summaries propagate unchanged. No API dispatch, threshold changes or held-out scoring.'})
    print(json.dumps(endpoints),flush=True)

if __name__=='__main__':main()
