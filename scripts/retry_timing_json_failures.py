"""Retry missing timing judgments unchanged, archiving malformed wire responses."""
import argparse,fcntl,hashlib,io,json,runpy,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--offset',type=int,choices=[32,64],required=True);a=p.parse_args()
    control=ROOT/'runs/controller';phase=ROOT/f'runs/fresh-offset{a.offset}-jview-test';helper=ROOT/'scripts/interpret_fresh_openrouter.py'
    # Wait for the current sequencer and its child to finish; never overlap requests.
    guard=(control/'earlier-position-scoring.lock').open('a');fcntl.flock(guard,fcntl.LOCK_EX)
    phaseguard=(phase/'lock').open('a');fcntl.flock(phaseguard,fcntl.LOCK_EX);fcntl.flock(phaseguard,fcntl.LOCK_UN);phaseguard.close()
    out=phase/'response-failures';out.mkdir(exist_ok=True)
    (out/'audit-wrapper.json').write_text(json.dumps({'wrapper_sha256':sha(Path(__file__)),'helper_sha256':sha(helper),'scope':'Observes response bytes without modifying payload, response parsing, threshold or successful cached judgments; maximum two additional passes'})+'\n')
    original=urllib.request.urlopen
    def observed(req,*args,**kwargs):
        response=original(req,*args,**kwargs)
        if not isinstance(req,urllib.request.Request) or req.full_url!='https://openrouter.ai/api/v1/chat/completions':return response
        with response:body=response.read()
        problem=False
        try:
            raw=json.loads(body);content=raw['choices'][0]['message']['content'];json.loads(content)
        except (ValueError,KeyError,TypeError):problem=True
        if problem:
            digest=hashlib.sha256(req.data+body).hexdigest()
            (out/(digest+'.json')).write_text(json.dumps({'sent_request':json.loads(req.data),'raw_response_text':body.decode('utf-8',errors='replace')},indent=2)+'\n')
        return io.BytesIO(body)
    urllib.request.urlopen=observed
    attempts=[]
    for attempt in range(2):
        current=json.loads((phase/'complete.json').read_text())
        if not current['errors']:break
        attempts.append({'before_errors':len(current['errors'])})
        sys.argv=[str(helper),'--phase','test','--offset',str(a.offset),'--workers','4']
        runpy.run_path(str(helper),run_name='__main__')
        current=json.loads((phase/'complete.json').read_text());attempts[-1]['after_errors']=len(current['errors'])
    urllib.request.urlopen=original
    final=json.loads((phase/'complete.json').read_text())
    (out/'retry-result.json').write_text(json.dumps({'attempts':attempts,'remaining_errors':final['errors'],'complete_sha256':sha(phase/'complete.json')},indent=2)+'\n')
    assert not final['errors'],'Malformed judgments remain; inspect archived raw responses'
    fcntl.flock(guard,fcntl.LOCK_UN);guard.close()
    subprocess.run([sys.executable,str(ROOT/'scripts/resume_earlier_openrouter.py'),'--wait'],check=True)
if __name__=='__main__':main()
