"""Classify unavailable reviews using archived provider refusals, without relabeling."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate_missing(folder):
    complete=json.loads((folder/'complete.json').read_text())
    if not complete['errors']:return None
    report=json.loads((folder/'documented-unavailable.json').read_text())
    assert report['complete_sha256']==sha(folder/'complete.json')
    expected={(r['episode_id'],r['arm'],r['model']) for r in complete['errors']}
    assert expected=={tuple(r['key']) for r in report['unavailable']}
    for row in report['unavailable']:
        assert row['reason']=='provider_policy_refusal' and row['evidence']
        for name,digest in row['evidence'].items():assert sha(folder/name)==digest
    return report
def main():
    p=argparse.ArgumentParser();p.add_argument('--offset',type=int,choices=[64],required=True);a=p.parse_args()
    folder=ROOT/f'runs/fresh-offset{a.offset}-jview-test';complete=json.loads((folder/'complete.json').read_text());aliases={hashlib.sha256(r['episode_id'].encode()).hexdigest()[:16]:r['episode_id'] for r in json.loads((ROOT/f'runs/fresh-offset{a.offset}-assembled/test-readouts.json').read_text())}
    evidence={};models={'openai/gpt-4.1':'gpt-4.1-2025-04-14','openai/gpt-5.4':'gpt-5.4'}
    for path in (folder/'response-failures').glob('*.json'):
        item=json.loads(path.read_text())
        if 'raw_response_text' not in item:continue
        raw=json.loads(item['raw_response_text']);choice=raw.get('choices',[{}])[0];error=choice.get('error',{})
        if choice.get('finish_reason')!='error' or error.get('code')!=400 or 'usage policy' not in error.get('message',''):continue
        request=item['sent_request'];payload=json.loads(request['messages'][1]['content']);key=(aliases[payload['case']],payload['arm'],models[request['model']]);evidence.setdefault(key,{})[str(path.relative_to(folder))]=sha(path)
    rows=[]
    for error in complete['errors']:
        key=(error['episode_id'],error['arm'],error['model']);assert key in evidence,('Unclassified failure',key)
        rows.append({'key':key,'reason':'provider_policy_refusal','evidence':evidence[key]})
    report={'complete_sha256':sha(folder/'complete.json'),'unavailable':rows,'script_sha256':sha(Path(__file__)),'scope':'Provider-refused judgments remain unavailable. No prompt changes, replacement reviewers, inferred scores, or clean-negative counting. Original failed completion and score files remain unchanged.'}
    (folder/'documented-unavailable.json').write_text(json.dumps(report,indent=2)+'\n');validate_missing(folder);print('Documented provider refusals:',len(rows))
if __name__=='__main__':main()
