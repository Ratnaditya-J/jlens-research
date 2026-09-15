"""Trusted CPU controller: collect, WASI-review, gate prepared jobs, stop tracked GPUs.

No generated model code is executed natively. Secrets live outside the repository.
This is a deterministic stage runner, not a replacement for Codex research reasoning.
"""
import datetime as dt,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=Path('/workspace/private')
os.environ.update(json.loads((PRIVATE/'controller-credentials.json').read_text()))
from runpod_control import api,sanitized
STATES={'confirmation':ROOT/'runs/pod.json','benchmark':ROOT/'runs/pod-benchmark.json'}
OUT=ROOT/'runs/controller';OUT.mkdir(parents=True,exist_ok=True)
def write(path,obj):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(obj,indent=2)+'\n');temp.replace(path)
def ssh_args(state):
    pod=state['pod'];return ['ssh','-i',str(PRIVATE/'pod_ed25519'),'-o','UserKnownHostsFile='+str(PRIVATE/'known_hosts'),'-o','ConnectTimeout=15','-o','ServerAliveInterval=30','-p',str(pod['portMappings']['22'])]
def remote(state,command):
    return subprocess.run(ssh_args(state)+['root@'+state['pod']['publicIp'],command],capture_output=True,text=True,timeout=60,check=True).stdout
def sync(state,source,dest,upload=False):
    dest=Path(dest) if not upload else dest
    if not upload:dest.mkdir(parents=True,exist_ok=True)
    endpoint='root@'+state['pod']['publicIp']+':'
    # Known paths contain no spaces; SSH's command string is generated from fixed arguments.
    command=['rsync','-rt','--timeout=90','-e',' '.join(ssh_args(state))]
    command += [str(source),endpoint+str(dest)] if upload else [endpoint+source,str(dest)+'/']
    subprocess.run(command,check=True,capture_output=True,text=True,timeout=180)
def stop(role,state,reason,path=None):
    api('pods/'+state['pod']['id']+'/stop','POST')
    state.update(stopped_at=dt.datetime.now(dt.timezone.utc).isoformat(),stop_reason=reason)
    state['pod']['desiredStatus']='EXITED';write(path or STATES[role],state)
def collect_replay():
    for shard in range(2):
        path=ROOT/f'runs/pod-replay-{shard}.json'
        if not path.exists():continue
        state=json.loads(path.read_text())
        if state.get('terminated'):continue
        state['pod']=sanitized(api('pods/'+state['pod']['id']));write(path,state)
        if state['pod']['desiredStatus']!='RUNNING' or not state['pod'].get('portMappings'):continue
        now=dt.datetime.now(dt.timezone.utc)
        if now>=dt.datetime.fromisoformat(state['deadline']):
            stop('replay',state,'replay deadline',path);continue
        directory=ROOT/f'runs/replay-{shard}'
        sync(state,f'/workspace/jlens-research/runs/replay-{shard}/',directory)
        finished=directory/'complete.json'
        if finished.exists():
            c=json.loads(finished.read_text())
            assert all((directory/name).exists() and hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest for name,digest in c['files_sha256'].items())
            idle=directory/'controller-completion-seen.json'
            if not idle.exists():write(idle,{'at':now.isoformat()})
            elapsed=(now-dt.datetime.fromisoformat(json.loads(idle.read_text())['at'])).total_seconds()
            if elapsed>=900:stop('replay',state,'replay complete; verified artifacts; warm grace elapsed',path)

def tick():
    collect_replay()
    active=ROOT/'configs/active-stage.json'
    if active.exists():
        stage=json.loads(active.read_text());now=dt.datetime.now(dt.timezone.utc);rows=[]
        stage_states={role:ROOT/'runs'/name for role,name in stage.get('state_files',{k:v.name for k,v in STATES.items()}).items()}
        for shard,(role,path) in enumerate(stage_states.items()):
            state=json.loads(path.read_text())
            state['pod']=sanitized(api('pods/'+state['pod']['id']));write(path,state)
            row={'shard':shard,'status':state['pod']['desiredStatus']}
            if state['pod']['desiredStatus']=='RUNNING':
                if now>=dt.datetime.fromisoformat(state['deadline']):stop(role,state,'remote deadline',path)
                elif state['pod'].get('portMappings'):
                    directory=ROOT/f"runs/{stage['name']}-{shard}"
                    sync(state,f"/workspace/jlens-research/runs/{stage['name']}-{shard}/",directory)
                    finished=directory/'complete.json'
                    if finished.exists():
                        complete=json.loads(finished.read_text());lens=directory/'lens.pt'
                        if lens.exists() and hashlib.sha256(lens.read_bytes()).hexdigest()==complete['lens_sha256']:
                            row['complete']=complete
                            idle=directory/'controller-completion-seen.json'
                            if not idle.exists():write(idle,{'at':now.isoformat()})
                            elapsed=(now-dt.datetime.fromisoformat(json.loads(idle.read_text())['at'])).total_seconds()
                            if elapsed>=stage.get('warm_idle_grace_seconds',900):
                                stop(role,state,'stage complete; verified outputs; warm idle grace elapsed',path)
            rows.append(row)
        write(OUT/'status.json',{'at':now.isoformat(),'active_stage':stage['name'],'shards':rows})
        return
    states={k:json.loads(p.read_text()) for k,p in STATES.items()}
    now=dt.datetime.now(dt.timezone.utc)
    for role,state in states.items():
        if state.get('terminated'):continue
        state['pod']=sanitized(api('pods/'+state['pod']['id']));write(STATES[role],state)
        if state['pod']['desiredStatus']!='RUNNING':continue
        if now>=dt.datetime.fromisoformat(state['deadline']):
            # Stop preserves the attached workspace volume even if collection fails.
            stop(role,state,'remote controller deadline');continue
        if not state['pod'].get('portMappings'):continue
        if role=='confirmation':
            sync(state,'/workspace/jlens-research/runs/confirmation/',ROOT/'runs/confirmation')
        else:
            sync(state,'/workspace/jlens-research/runs/',ROOT/'runs/benchmark-remote')
            if (ROOT/'configs/parallel-tail.json').exists():
                tail=ROOT/'runs/benchmark-remote/confirmation-tail'
                if tail.exists():
                    subprocess.run(['rsync','-rt','--exclude','complete.json','--exclude','progress.json',str(tail)+'/',str(ROOT/'runs/confirmation')+'/'],check=True,capture_output=True,timeout=90)
    with (OUT/'review.log').open('a') as log:
        subprocess.run([sys.executable,str(ROOT/'scripts/review_batch.py'),str(ROOT/'runs/confirmation'),'--workers','8'],stdout=log,stderr=log,timeout=900,check=True)
    reviewed=json.loads((ROOT/'runs/confirmation/review-summary.json').read_text())
    counts=reviewed['counts'];numerics=ROOT/'runs/benchmark-remote/lens-numerics/report.json';speed=ROOT/'runs/benchmark-remote/speed-benchmark/report.json'
    pipeline_done=(ROOT/'runs/benchmark-remote/benchmark-complete').exists()
    generation_done=(ROOT/'runs/confirmation/complete.json').exists()
    if (ROOT/'configs/parallel-tail.json').exists():
        generation_done=generation_done and (ROOT/'runs/benchmark-remote/confirmation-tail/complete.json').exists()
    gate_ready=counts.get('misaligned',0)>=30 and counts.get('benign',0)>=30 and numerics.exists() and speed.exists()
    if gate_ready and pipeline_done and generation_done:
        n=json.loads(numerics.read_text());s=json.loads(speed.read_text())
        valid=[b for b in s['fitting_batches'] if b.get('passed')]
        if n.get('passed') and valid:
            best=min(valid,key=lambda b:b['seconds_for_32_rows'])
            gate={'numerics_passed':True,'positives':counts['misaligned'],'benign':counts['benign'],'dim_batch':best['dim_batch'],
                  'numerics_sha256':hashlib.sha256(numerics.read_bytes()).hexdigest(),'speed_sha256':hashlib.sha256(speed.read_bytes()).hexdigest()}
            write(ROOT/'configs/fit-pilot-gate.json',gate)
            for shard,role in enumerate(('confirmation','benchmark')):
                state=states[role];marker=OUT/f'fit-{shard}-launched.json'
                if marker.exists() or state['pod']['desiredStatus']!='RUNNING':continue
                remaining=(dt.datetime.fromisoformat(state['deadline'])-now).total_seconds()-120
                if remaining<best['estimated_seconds_per_2880_row_prompt']*2*1.5:continue
                for script in ('fit_pilot_shard.py','gptoss_lens_model.py'):
                    sync(state,ROOT/'scripts'/script,'/workspace/jlens-research/scripts/',upload=True)
                for config in ('fit-pilot-gate.json','generic-corpus.json'):
                    sync(state,ROOT/'configs'/config,'/workspace/jlens-research/configs/',upload=True)
                timeout=min(7200,int(remaining))
                remote(state,f'mkdir -p /workspace/jlens-research/runs/fit-pilot-{shard}')
                command=f'nohup timeout --kill-after=60 {timeout} /workspace/jlens-venv/bin/python -u /workspace/jlens-research/scripts/fit_pilot_shard.py --shard {shard} --dim-batch {best["dim_batch"]} > /workspace/jlens-research/runs/fit-pilot-{shard}/console.log 2>&1 < /dev/null &'
                # Detach all descriptors so SSH can finish while the GPU job runs.
                remote(state,command);write(marker,{'at':now.isoformat(),'pod':state['pod']['id'],'gate':gate})
        else:
            write(OUT/'scientific-attention.json',{'at':now.isoformat(),'reason':'Numerical or batching validation failed; preserve diagnostics, no fitting promotion'})
    for shard,role in enumerate(('confirmation','benchmark')):
        state=states[role]
        if state['pod']['desiredStatus']!='RUNNING':continue
        launched=(OUT/f'fit-{shard}-launched.json').exists()
        if launched:
            sync(state,f'/workspace/jlens-research/runs/fit-pilot-{shard}/',ROOT/f'runs/fit-pilot-{shard}')
            finished=ROOT/f'runs/fit-pilot-{shard}/complete.json'
            if finished.exists():
                lens=finished.parent/'lens.pt'
                expected=json.loads(finished.read_text())['lens_sha256']
                if lens.exists() and hashlib.sha256(lens.read_bytes()).hexdigest()==expected:
                    stop(role,state,'fit pilot complete; outputs checksum-verified on controller')
        elif pipeline_done and generation_done and (OUT/'scientific-attention.json').exists():
            stop(role,state,'prepared stages complete; validation needs diagnosis')
    write(OUT/'status.json',{'at':now.isoformat(),'reviewed':reviewed['completed_episodes'],'counts':counts,'benchmark_complete':pipeline_done,'generation_complete':generation_done,'states':{k:v['pod']['desiredStatus'] for k,v in states.items()}})
if __name__=='__main__':
    import fcntl
    lock=(OUT/'controller.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (OUT/'pid').write_text(str(os.getpid()))
    while True:
        try:
            tick()
            error_path=OUT/'last-error.json'
            if error_path.exists():error_path.replace(OUT/'previous-resolved-error.json')
        except Exception as error:
            write(OUT/'last-error.json',{'at':dt.datetime.now(dt.timezone.utc).isoformat(),'type':type(error).__name__,'message':str(error)[:600]})
        time.sleep(120)
