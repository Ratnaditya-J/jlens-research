"""Offline reference provenance and candidate-disagreement audit; no relabeling."""
import argparse
import json
from collections import Counter
from pathlib import Path
from contracts import fingerprint, parse_json_reply
from local_judge_bridge import build
from smoke import digest, write_json
from collect_local_readers import valid_score


def audit(bridge,scores,cache,readers):
    protocol=json.loads((bridge/'protocol.json').read_text())
    for key,path in [('source_scores',scores),('jobs',bridge/'jobs.json'),('references',bridge/'references.json')]:
        if digest(path)!=protocol[key+'_sha256']:raise ValueError('Bridge source changed')
    jobs,refs=build(json.loads(scores.read_text()),cache)
    if {'jobs':jobs}!=json.loads((bridge/'jobs.json').read_text()) or {'references':refs}!=json.loads((bridge/'references.json').read_text()):raise ValueError('Rebuilt selection differs')
    jobs={x['request_id']:x for x in jobs};rows=[];matrices={name:Counter() for name in readers}
    for ref in refs:
        rid=ref['request_id'];reference_judgments=[];source_hashes={}
        for sha in ref['cached_request_sha256']:
            cached_path=cache/(sha+'.json');cached=json.loads(cached_path.read_text())
            if cached['request_sha256']!=sha:raise ValueError('Cache identity differs')
            raw_paths=sorted(cache.glob(sha+'-raw-*.json'))
            # Match the accepted cached response, not an arbitrary retry.
            matched=[]
            for path in raw_paths:
                raw=json.loads(path.read_text())
                if raw['response'].get('id')==cached['response_id']:matched.append((path,raw))
            if len(matched)!=1:raise ValueError('Accepted reference receipt missing or ambiguous')
            path,raw=matched[0];request=raw['request']
            if fingerprint(request)!=sha:raise ValueError('Raw request hash differs')
            payload={'system':request['messages'][0]['content'],'evidence':json.loads(request['messages'][1]['content'])}
            if fingerprint(payload)!=rid:raise ValueError('Reference evidence differs')
            judgment=parse_json_reply(raw['response']['choices'][0]['message']['content'])
            if judgment!=cached['judgment'] or type(judgment.get('score')) is not int or judgment['score']!=ref['reference_score']:raise ValueError('Reference consensus differs from accepted raw reply')
            reference_judgments.append({'requested_model':request['model'],'resolved_model':raw['response']['model'],'judgment':judgment})
            source_hashes[str(path.resolve())]=digest(path);source_hashes[str(cached_path.resolve())]=digest(cached_path)
        if {x['requested_model'] for x in reference_judgments}!={'openai/gpt-4.1','openai/gpt-5.4'}:raise ValueError('Reference family identity differs')
        candidate_scores={}
        for name,reader in readers.items():
            manifest=json.loads((reader/'manifest.json').read_text());path=reader/'results'/(rid+'.json');result=json.loads(path.read_text())
            if result['request_id']!=rid or result['manifest_sha256']!=fingerprint(manifest):raise ValueError('Candidate result identity differs')
            score=valid_score(result);candidate_scores[name]=score;matrices[name][(ref['reference_score'],score)]+=1;source_hashes[str(path.resolve())]=digest(path)
        rows.append({**ref,'reference_judgments':reference_judgments,'candidate_scores':candidate_scores,'source_sha256':source_hashes})
    return {'reference_provenance_passed':True,'n':len(rows),'reference_models':['openai/gpt-4.1','openai/gpt-5.4'],'confusion_counts':{name:[{'reference':a,'candidate':b,'n':n} for (a,b),n in sorted(counts.items(),key=lambda x:str(x[0]))] for name,counts in matrices.items()},'rows':rows,'scope':'Development reference provenance and disagreement only. No corrected labels, gate relaxation, model adoption or held-out performance. Candidate results are adaptively selected and not independent accuracy estimates.'}


def main():
    p=argparse.ArgumentParser()
    for name in ['bridge','scores','cache','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reader',action='append',default=[],help='name=directory');a=p.parse_args()
    if a.out.exists():raise ValueError('Preserve audit')
    readers={name:Path(path) for name,path in (x.split('=',1) for x in a.reader)}
    report=audit(a.bridge,a.scores,a.cache,readers);write_json(a.out,report);print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
