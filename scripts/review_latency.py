"""Summarize recorded reviewer API latency and usage, without price assumptions."""
import argparse,hashlib,json,math
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def distribution(values):
    values=sorted(values)
    if not values:return {'n':0}
    assert all(math.isfinite(v) and v>=0 for v in values)
    def q(p):
        index=p*(len(values)-1);lo=int(index);hi=min(lo+1,len(values)-1)
        return values[lo]+(values[hi]-values[lo])*(index-lo)
    return {'n':len(values),'min':values[0],'median':q(.5),'p90':q(.9),'p95':q(.95),'max':values[-1],'mean':sum(values)/len(values)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dataset',choices=['development','primary','template-challenge'],required=True);args=parser.parse_args()
    stem={'development':'jview-interpretation-v1','primary':'fresh-jview-test','template-challenge':'template-challenge-jview-test'}[args.dataset]
    directory=ROOT/'runs'/stem;complete=json.loads((directory/'complete.json').read_text());assert not complete['errors']
    groups=defaultdict(list);per_case=defaultdict(list);usage=defaultdict(lambda:defaultdict(int));hashes={}
    for p in sorted((directory/'reviews').glob('*/*.json')):
        r=json.loads(p.read_text());key=r['arm']+' / '+r['resolved_model'];elapsed=r['elapsed_seconds']
        groups[key].append(elapsed);per_case[(r['episode_id'],r['arm'])].append(elapsed)
        u=r.get('usage') or {}
        for name in ['prompt_tokens','completion_tokens','total_tokens']:usage[key][name]+=u.get(name,0)
        usage[key]['cached_prompt_tokens']+=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0)
        hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    assert sum(len(v) for v in groups.values())==complete['completed_calls']
    arm_elapsed=defaultdict(list)
    for (eid,arm),values in per_case.items():
        assert len(values)==2,'Expected two valid reviewers per arm'
        arm_elapsed[arm].append(max(values))
    gpu_components={}
    if args.dataset!='development':
        processed='fresh' if args.dataset=='primary' else 'template-challenge'
        times=defaultdict(list);ids={eid for eid,arm in per_case};found=set()
        for shard in range(4):
            for eid in ids:
                path=ROOT/f'runs/{processed}-processed-{shard}'/eid/'timings.json'
                if not path.exists():continue
                assert eid not in found;found.add(eid)
                manifest=json.loads(path.with_name('complete.json').read_text())
                assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['files_sha256']['timings.json']
                for row in json.loads(path.read_text())['positions']:
                    for key in ['replay_seconds','display_seconds']:
                        if row.get(key) is not None:times[str(row['offset'])+' / '+key].append(row[key])
        gpu_components={'by_offset_seconds':{k:distribution(v) for k,v in times.items()},'cases_with_timing':len(found),'reviewed_cases':len(ids),'scope':'GPU-synchronized readout components for cases with reviewer records; replay excludes model loading, display includes reference transport/native unembedding/top20 and candidate ranking; components are from offline processing'}
    report={'dataset':args.dataset,'gpu_readout_components':gpu_components,'per_call_elapsed_seconds':{k:distribution(v) for k,v in groups.items()},'paired_review_max_call_seconds':{k:distribution(v) for k,v in arm_elapsed.items()},'token_usage':{k:dict(v) for k,v in usage.items()},'scope':'Recorded automated-review request elapsed time, including request retries/backoff where present. Max of two per-call durations is an idealized parallel-review component, not measured total decision latency.','excluded_from_latency':['Waiting for worker scheduling/queue','Model trajectory generation and activation extraction','J-space transport and vocabulary/display construction','Artifact writing and downstream joining'],'limitations':['Not human review time','Concurrent call durations must not be summed and called elapsed wall time','No currency cost inferred without pinned billing rates; token usage is not an invoice','Offline benchmark, not demonstrated real-time monitoring'],'source_sha256':hashes}
    out=ROOT/f'reports/review-latency-{args.dataset}.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['dataset','paired_review_max_call_seconds','per_call_elapsed_seconds']}))

if __name__=='__main__':main()
