"""Report timing results restricted to original direct-API review availability."""
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--offset',type=int,choices=[32,64],required=True);a=p.parse_args()
    folder=ROOT/f'reports/final-comparison-offset{a.offset}';source=ROOT/f'runs/fresh-offset{a.offset}-jview-test';summary=folder/'summary.json';cases=folder/'cases.json';rows=json.loads(cases.read_text());review_hashes={};routes={};counts=Counter()
    for r in rows:
        files=list((source/'reviews'/r['episode_id']).glob('*.json'));providers=[]
        for path in files:
            j=json.loads(path.read_text());route=j.get('transport',{}).get('gateway','direct OpenAI');providers.append(route);counts[route]+=1;review_hashes[str(path.relative_to(ROOT))]=sha(path)
        routes[r['episode_id']]='direct_only' if len(providers)==4 and all(x=='direct OpenAI' for x in providers) else ('contains_supplement' if 'OpenRouter' in providers else 'incomplete')
    groups={}
    for group in ['all','direct_only','contains_supplement','incomplete']:
        selected=[r for r in rows if group=='all' or routes[r['episode_id']]==group]
        paired=[r for r in selected if r.get('category') in ['probe_only','jlens_only','both','neither'] and r['behavior_label'] in ['misaligned','benign']]
        tables={label:{c:sum(r['behavior_label']==label and r['category']==c for r in paired) for c in ['probe_only','jlens_only','both','neither']} for label in ['misaligned','benign']}
        metrics={}
        for method in ['probe','jlens']:
            positives=[r for r in paired if r['behavior_label']=='misaligned'];benign=[r for r in paired if r['behavior_label']=='benign'];tp=sum(r[method+'_flag'] for r in positives);fp=sum(r[method+'_flag'] for r in benign)
            metrics[method]={'tp':tp,'fn':len(positives)-tp,'fp':fp,'tn':len(benign)-fp,'sensitivity':tp/len(positives) if positives else None,'fpr':fp/len(benign) if benign else None}
        groups[group]={'rows':len(selected),'known_paired':len(paired),'tables':tables,'metrics':metrics,'episode_ids':[r['episode_id'] for r in paired]}
    result={'offset':a.offset,'review_counts_by_gateway':dict(counts),'groups':groups,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [summary,cases,Path(__file__)]},'review_sha256':review_hashes,'scope':'Available-case sensitivity analysis; API failure timing was not randomized and groups may differ in task composition. No provider-equivalence claim or replacement of the complete secondary result.'}
    (folder/'transport-sensitivity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'offset':a.offset,'reviews':dict(counts),'direct_only':groups['direct_only']['metrics']}))
if __name__=='__main__':main()
