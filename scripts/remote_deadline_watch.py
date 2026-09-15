"""Independent deadline enforcement, unaffected by controller reviews or laptop sleep."""
import datetime as dt,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.update(json.loads(Path('/workspace/private/controller-credentials.json').read_text()))
from runpod_control import api
done=set()
if __name__=='__main__':
    import fcntl
    lock=(ROOT/'runs/controller/deadline.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    while True:
        for name in ('pod.json','pod-benchmark.json'):
            state=json.loads((ROOT/'runs'/name).read_text());pid=state['pod']['id']
            if pid in done or state.get('terminated'):continue
            now=dt.datetime.now(dt.timezone.utc)
            if now<dt.datetime.fromisoformat(state['deadline']):continue
            try:
                current=api('pods/'+pid)
                if current['desiredStatus']=='RUNNING':api('pods/'+pid+'/stop','POST')
                with (ROOT/'runs/controller/deadline-events.jsonl').open('a') as out:
                    out.write(json.dumps({'at':now.isoformat(),'pod_id':pid,'event':'deadline enforced'})+'\n')
                done.add(pid)
            except Exception as error:print(type(error).__name__,str(error),flush=True)
        time.sleep(30)
