"""Cache legacy validation judgments that do not depend on summaries."""
import argparse
import json
from pathlib import Path
from legacy_local_jobs import prepare
from smoke import digest, write_json


def independent_jobs(views, contexts, base):
    jobs, aliases, donors=prepare(views,contexts,base,{})
    aliases=[a for a in aliases if not a['arm'].startswith('jsummary')]
    ids={a['request_id'] for a in aliases if a['request_id'] is not None}
    return [j for j in jobs if j['request_id'] in ids],aliases,donors


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('Preserve existing prepared requests')
    vp=a.repo/'runs/fresh-assembled/validation-readouts.json';cp=a.repo/'runs/fresh-assembled/validation-contexts.json';bp=a.repo/'configs/jview-final-v1.json'
    views=json.loads(vp.read_text());contexts={r['episode_id']:r for r in json.loads(cp.read_text())['rows']};base=json.loads(bp.read_text())
    jobs,aliases,donors=independent_jobs(views,contexts,base)
    a.out.mkdir(parents=True)
    write_json(a.out/'jobs.json',{'jobs':sorted(jobs,key=lambda j:j['request_id'])})
    write_json(a.out/'aliases.json',aliases)
    sources=[vp,cp,bp,Path(__file__),Path(__file__).with_name('legacy_local_jobs.py'),Path(__file__).with_name('local_reader_jobs.py')]
    write_json(a.out/'manifest.json',{'study':'archived-gptoss-local-extension-v1','dataset':'fresh','phase':'validation','stage':'summary-independent-reviews','arms':['jview_blind','jview','context_only'],'jobs_sha256':digest(a.out/'jobs.json'),'aliases_sha256':digest(a.out/'aliases.json'),'donors':donors,'source_hashes':{str(p.resolve()):digest(p) for p in sources},'scope':'Partial validation inference cache for the separate local protocol. No test requests, no new trajectories, no replacement of frozen premium judgments. Uses the identical full-review payload builder.'})
    print(json.dumps({'unique_requests':len(jobs),'aliases':len(aliases)}))

if __name__=='__main__':main()
