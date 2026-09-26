"""Blind top-10 summarizer control over immutable original GPT-OSS readouts."""
import argparse,concurrent.futures,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'studies/reader_comparison'))
from api_client import request_json
from contracts import fingerprint
from smoke import write_json,digest
PROMPT='You are shown the top-10 token readouts from an interpretability lens at one position inside a language model that was reading a passage you cannot see. Tokens may include noise, fragments, other languages (translate them), or byte artifacts. In one or two sentences, state what these outputs are collectively trying to say — the situation or mental content they point to. Commit to the most specific reading the tokens support; do not just say they are noisy.'
def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['validation','test'],required=True);p.add_argument('--offset',type=int,default=0);p.add_argument('--dataset',default='fresh');p.add_argument('--credential-file',type=Path,required=True);p.add_argument('--workers',type=int,default=12);a=p.parse_args();suffix=f'-offset{a.offset}' if a.offset else '';stem=a.dataset+suffix
 cfgpath=ROOT/'configs/jsummary-v1.json';cfg=json.loads(cfgpath.read_text());source=ROOT/f'runs/{stem}-assembled/{a.phase}-readouts.json';out=ROOT/f'runs/{stem}-jsummary-{a.phase}';out.mkdir(parents=True,exist_ok=True)
 if a.phase=='test' and not (ROOT/f'runs/fresh{suffix}-jsummary-calibration/lock.json').exists():raise ValueError('Lock new validation thresholds before test')
 manifest={'readouts_sha256':digest(source),'config_sha256':digest(cfgpath),'script_sha256':digest(__file__),'scope':'Per-layer blind summary; no labels, context, candidate ranks or other-reader outputs'}
 mp=out/'summary-manifest.json'
 if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Changed summary provenance')
 write_json(mp,manifest);views=json.loads(source.read_text());jobs=[(v['episode_id'],l) for v in views for l in v['layers']]
 def run(job):
  eid,l=job;bag=' | '.join(f"{t['text']} ({t['logit']:.2f})" for t in l['top_tokens'][:10]);r=request_json(cfg['summarizer_model'],PROMPT+' Return JSON with exactly one nonempty string field: interpretation.',{'TOKEN READOUTS':bag},ROOT/'runs/jsummary-api-cache',a.credential_file,max_tokens=1600)
  text=r['judgment'].get('interpretation')
  if not isinstance(text,str) or not text.strip():raise ValueError('Unavailable interpretation')
  return {'episode_id':eid,'layer':l['layer'],'interpretation':text,'request_sha256':r['request_sha256']}
 results=[];errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
  futures={pool.submit(run,j):j for j in jobs}
  for f in concurrent.futures.as_completed(futures):
   try:results.append(f.result())
   except Exception as e:errors.append({'episode_id':futures[f][0],'layer':futures[f][1]['layer'],'error':str(e)})
   if (len(results)+len(errors))%25==0:write_json(out/'summary-progress.json',{'completed':len(results),'total':len(jobs),'errors':errors})
 results.sort(key=lambda x:(x['episode_id'],x['layer']));write_json(out/'summaries.json',results);write_json(out/'summary-complete.json',{'completed':len(results),'total':len(jobs),'errors':errors,'summaries_sha256':digest(out/'summaries.json'),'manifest_sha256':fingerprint(manifest)})
 print(json.dumps({'stem':stem,'completed':len(results),'errors':errors}),flush=True)
if __name__=='__main__':main()
