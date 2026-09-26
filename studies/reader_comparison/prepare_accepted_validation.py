"""Collect a completed accepted summary tranche and prepare validation arms only."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from collect_local_readers import load_jobs
from hosted_text_reader_lowreference import execution_manifest
from smoke import digest,write_json
from validate_reader_gates import ready
from verify_reader_acceptance import load_acceptance


def main():
    p=argparse.ArgumentParser()
    for name in ['bundle','summary-jobs','reader','acceptance','out']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--hours',type=float,default=2);a=p.parse_args()
    m,_,_=load_jobs(a.summary_jobs)
    if m['phase']!='validation' or m['stage']!='summaries' or m['endpoint']!='before_action' or m['bundle_sha256']!=digest(a.bundle):
        raise ValueError('Wrong registered validation summary inputs')
    sources=load_acceptance(a.acceptance,execution_manifest('gpt54lowreference'))
    deadline=time.monotonic()+a.hours*3600
    while not ready(a.reader,a.summary_jobs,'primary-validation-summary-jobs-complete.json'):
        if time.monotonic()>deadline:raise TimeoutError('Summary completion still pending; no preparation')
        time.sleep(10)
    if a.out.exists():raise ValueError('Preserve existing validation preparation')
    a.out.mkdir(parents=True);scripts=Path(__file__).parent;summary=a.out/'summaries.json'
    commands=[
        [sys.executable,str(scripts/'collect_local_readers.py'),'--jobs',str(a.summary_jobs),'--readers',str(a.reader),
         '--second-reader-family','gpt5','--reader-acceptances',str(a.acceptance),'--out',str(summary)],
        [sys.executable,str(scripts/'local_reader_jobs.py'),'--bundle',str(a.bundle),'--phase','validation','--stage','reviews',
         '--summaries',str(summary),'--out',str(a.out/'reviews')]]
    for i,command in enumerate(commands):
        with (a.out/f'stage-{i}.log').open('w') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
    for path in [a.bundle,summary,a.out/'reviews/manifest.json',a.out/'reviews/jobs.json',a.out/'reviews/aliases.json',Path(__file__)]:
        sources[str(path.resolve())]=digest(path)
    write_json(a.out/'complete.json',{'phase':'validation','commands':commands,'source_hashes':sources,
        'scope':'Prepared all nine arms from accepted summaries. No reviewer inference, calibration lock, held-out evaluation or detector performance.'})
    print(json.dumps({'prepared':str(a.out),'review_jobs':json.loads((a.out/'reviews/manifest.json').read_text())['jobs_sha256']}),flush=True)


if __name__=='__main__':main()
