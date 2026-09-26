"""Finish a stopped frozen review using saved responses only; never send HTTP."""
import argparse,json,runpy,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'studies/reader_comparison'))
import api_client
from contracts import fingerprint
from smoke import write_json,digest

def cached_only(model,system,evidence,cache,credential_file,max_tokens=1600):
 payload={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(evidence,ensure_ascii=False)}],'response_format':{'type':'json_object'},'max_tokens':max_tokens,'provider':{'require_parameters':True}}
 if model.startswith('openai/gpt-5'):payload['reasoning']={'effort':'low'}
 else:payload['temperature']=0
 key=fingerprint(payload);path=Path(cache)/(key+'.json')
 if not path.exists():raise RuntimeError('Cost amendment: no cached response; paid inference disabled')
 result=json.loads(path.read_text())
 if result['request_sha256']!=key or result['requested_model']!=model:raise ValueError('Invalid cached response')
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--offset',type=int,default=0);a=p.parse_args();suffix=f'-offset{a.offset}' if a.offset else '';out=ROOT/f'runs/fresh{suffix}-jsummary-test'
 if (out/'review-complete.json').exists():raise ValueError('Completed frozen review must not be rerun')
 api_client.request_json=cached_only
 sys.argv=[str(ROOT/'scripts/interpret_jsummary.py'),'--phase','test','--offset',str(a.offset),'--credential-file','UNUSED_NO_NETWORK']
 runpy.run_path(sys.argv[0],run_name='__main__')
 write_json(out/'offline-completion.json',{'reason':'User requested cost reduction; remaining uncached requests were unavailable rather than billed. Cached results and frozen rubric/thresholds retained. Missingness may depend on request order and completion latency; do not assume missing at random.','http_requests':0,'script_sha256':digest(__file__),'completed_at':time.time()})
if __name__=='__main__':main()
