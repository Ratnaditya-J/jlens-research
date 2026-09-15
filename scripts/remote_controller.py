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

def merge_fit64_if_ready():
    directories=[ROOT/f'runs/fit64-{i}' for i in range(4)]
    if not all((d/'complete.json').exists() for d in directories):return False
    for name,indices in [('fit64-merged',[0,1,2,3]),('fit64-half-a',[0,1]),('fit64-half-b',[2,3])]:
        dest=ROOT/'runs'/name
        if (dest/'report.json').exists():continue
        with (OUT/'merge64.log').open('a') as log:
            subprocess.run(['python',str(ROOT/'scripts/merge_fit_shards.py'),str(dest),*[str(directories[i]) for i in indices]],stdout=log,stderr=log,check=True,timeout=180,env={**os.environ,'OMP_NUM_THREADS':'2'})
    return True

def advance_challenge(shard,role,path,state):
    plan=ROOT/'configs/next-template-challenge.json'
    if not plan.exists():return False
    quality=ROOT/f'runs/readout64-worker-{shard}/report.json'
    if not quality.exists() or not json.loads(quality.read_text())['shard_readout_stability_passed']:
        write(OUT/f'challenge-{shard}-deferred.json',{'reason':'primary lens quality gate did not pass'})
        return False
    stage=json.loads(plan.read_text());cfgpath=ROOT/stage['config']
    assert hashlib.sha256(cfgpath.read_bytes()).hexdigest()==stage['configuration_sha256']
    cfg=json.loads(cfgpath.read_text());expected=cfg['episodes'][shard::4]
    marker=OUT/f'challenge-{shard}-launched.json'
    remaining=int((dt.datetime.fromisoformat(state['deadline'])-dt.datetime.now(dt.timezone.utc)).total_seconds())-90
    if not marker.exists():
        if remaining<1800:
            write(OUT/f'challenge-{shard}-deferred.json',{'reason':'insufficient existing pod time; needs another allocation','remaining_seconds':remaining})
            return False
        sync(state,cfgpath,'/workspace/jlens-research/configs/',upload=True)
        for name in ['postprocess_fresh.py','bootstrap_template_challenge.sh']:
            sync(state,ROOT/'scripts'/name,'/workspace/jlens-research/scripts/',upload=True)
        remote(state,f'mkdir -p /workspace/jlens-research/runs/template-challenge-shard-{shard} /workspace/jlens-research/runs/template-challenge-processed-{shard}')
        command=f'nohup timeout --kill-after=60 {remaining} bash /workspace/jlens-research/scripts/bootstrap_template_challenge.sh {shard} > /workspace/jlens-research/runs/template-challenge-shard-{shard}/console.log 2>&1 </dev/null &'
        remote(state,command)
        write(marker,{'at':dt.datetime.now(dt.timezone.utc).isoformat(),'pod_id':state['pod']['id'],'configuration_sha256':stage['configuration_sha256'],'timeout_seconds':remaining})
    dest=ROOT/'runs/template-challenge';dest.mkdir(parents=True,exist_ok=True)
    endpoint='root@'+state['pod']['publicIp']+f':/workspace/jlens-research/runs/template-challenge-shard-{shard}/'
    subprocess.run(['rsync','-rt','--timeout=90','--exclude=/complete.json','--exclude=/progress.json','--exclude=/console.log','--exclude=/error.txt','-e',' '.join(ssh_args(state)),endpoint,str(dest)+'/'],check=True,capture_output=True,timeout=240)
    status=remote(state,f'if test -f /workspace/jlens-research/runs/template-challenge-shard-{shard}/complete.json; then cat /workspace/jlens-research/runs/template-challenge-shard-{shard}/complete.json; fi')
    if status.strip():
        c=json.loads(status);assert c['configuration_sha256']==stage['configuration_sha256'] and c['episodes']==len(expected)
        for ep in expected:
            directory=dest/ep['episode_id'];record=json.loads((directory/'episode.json').read_text());assert record['config_sha256']==stage['configuration_sha256']
            if 'activation_sha256' in record:assert hashlib.sha256((directory/'activations.safetensors').read_bytes()).hexdigest()==record['activation_sha256']
        write(OUT/f'challenge-{shard}-complete.json',c)
    processed=ROOT/f'runs/template-challenge-processed-{shard}'
    sync(state,f'/workspace/jlens-research/runs/template-challenge-processed-{shard}/',processed)
    if (processed/'complete.json').exists():
        c=json.loads((processed/'complete.json').read_text());assert c['completed']==len(expected)
        for eid,digest in c['case_complete_sha256'].items():
            case=processed/eid/'complete.json';assert hashlib.sha256(case.read_bytes()).hexdigest()==digest
            for name,digest in json.loads(case.read_text())['files_sha256'].items():assert hashlib.sha256((case.parent/name).read_bytes()).hexdigest()==digest
        write(OUT/f'challenge-processed-{shard}-complete.json',c)
        if not advance_specificity(shard,role,path,state):
            stop(role,state,'primary and template challenge artifacts collected and verified',path)
    return True

def advance_specificity(shard,role,path,state):
    plan=ROOT/'configs/next-specificity-controls.json'
    if not plan.exists():return False
    quality=ROOT/f'runs/readout64-worker-{shard}/report.json'
    if not quality.exists() or not json.loads(quality.read_text())['shard_readout_stability_passed']:
        write(OUT/f'specificity-{shard}-deferred.json',{'reason':'primary lens quality gate did not pass'})
        return False
    stage=json.loads(plan.read_text());cfgpath=ROOT/stage['config']
    assert hashlib.sha256(cfgpath.read_bytes()).hexdigest()==stage['configuration_sha256']
    cfg=json.loads(cfgpath.read_text());expected=cfg['episodes'][shard::4]
    marker=OUT/f'specificity-{shard}-launched.json'
    remaining=int((dt.datetime.fromisoformat(state['deadline'])-dt.datetime.now(dt.timezone.utc)).total_seconds())-90
    if not marker.exists():
        if remaining<900:
            write(OUT/f'specificity-{shard}-deferred.json',{'reason':'insufficient existing pod time; needs another allocation','remaining_seconds':remaining})
            return False
        sync(state,cfgpath,'/workspace/jlens-research/configs/',upload=True)
        for name in ['postprocess_fresh.py','bootstrap_specificity_controls.sh']:
            sync(state,ROOT/'scripts'/name,'/workspace/jlens-research/scripts/',upload=True)
        remote(state,f'mkdir -p /workspace/jlens-research/runs/specificity-controls-shard-{shard} /workspace/jlens-research/runs/specificity-controls-processed-{shard}')
        command=f'nohup timeout --kill-after=60 {remaining} bash /workspace/jlens-research/scripts/bootstrap_specificity_controls.sh {shard} > /workspace/jlens-research/runs/specificity-controls-shard-{shard}/console.log 2>&1 </dev/null &'
        remote(state,command)
        write(marker,{'at':dt.datetime.now(dt.timezone.utc).isoformat(),'pod_id':state['pod']['id'],'configuration_sha256':stage['configuration_sha256'],'timeout_seconds':remaining})
    dest=ROOT/'runs/specificity-controls';dest.mkdir(parents=True,exist_ok=True)
    endpoint='root@'+state['pod']['publicIp']+f':/workspace/jlens-research/runs/specificity-controls-shard-{shard}/'
    subprocess.run(['rsync','-rt','--timeout=90','--exclude=/complete.json','--exclude=/progress.json','--exclude=/console.log','--exclude=/error.txt','-e',' '.join(ssh_args(state)),endpoint,str(dest)+'/'],check=True,capture_output=True,timeout=240)
    status=remote(state,f'if test -f /workspace/jlens-research/runs/specificity-controls-shard-{shard}/complete.json; then cat /workspace/jlens-research/runs/specificity-controls-shard-{shard}/complete.json; fi')
    if status.strip():
        c=json.loads(status);assert c['configuration_sha256']==stage['configuration_sha256'] and c['episodes']==len(expected)
        for ep in expected:
            directory=dest/ep['episode_id'];record=json.loads((directory/'episode.json').read_text());assert record['config_sha256']==stage['configuration_sha256']
            if 'activation_sha256' in record:assert hashlib.sha256((directory/'activations.safetensors').read_bytes()).hexdigest()==record['activation_sha256']
        write(OUT/f'specificity-{shard}-complete.json',c)
    processed=ROOT/f'runs/specificity-controls-processed-{shard}'
    sync(state,f'/workspace/jlens-research/runs/specificity-controls-processed-{shard}/',processed)
    if (processed/'complete.json').exists():
        c=json.loads((processed/'complete.json').read_text());assert c['completed']==len(expected)
        for eid,digest in c['case_complete_sha256'].items():
            case=processed/eid/'complete.json';assert hashlib.sha256(case.read_bytes()).hexdigest()==digest
            for name,digest in json.loads(case.read_text())['files_sha256'].items():assert hashlib.sha256((case.parent/name).read_bytes()).hexdigest()==digest
        write(OUT/f'specificity-processed-{shard}-complete.json',c)
        stop(role,state,'primary, template challenge and specificity control artifacts collected and verified',path)
    return True

def advance_fresh(shard,role,path,state):
    next_path=ROOT/'configs/next-generation.json'
    if not next_path.exists():return False
    stage=json.loads(next_path.read_text());cfg_path=ROOT/stage['config']
    assert hashlib.sha256(cfg_path.read_bytes()).hexdigest()==stage['configuration_sha256']
    cfg=json.loads(cfg_path.read_text());marker=OUT/f'fresh-{shard}-launched.json';now=dt.datetime.now(dt.timezone.utc)
    if not marker.exists():
        remaining=int((dt.datetime.fromisoformat(state['deadline'])-now).total_seconds())-90
        if remaining<300:return False
        sync(state,cfg_path,'/workspace/jlens-research/configs/',upload=True)
        sync(state,ROOT/'scripts/behavior_pilot.py','/workspace/jlens-research/scripts/',upload=True)
        remote(state,f'mkdir -p /workspace/jlens-research/runs/fresh-shard-{shard} /workspace/jlens-research/runs/speed-benchmark')
        sync(state,ROOT/'runs/speed-benchmark/report.json','/workspace/jlens-research/runs/speed-benchmark/',upload=True)
        command=f'nohup env IDENTITY_CONFIG=configs/identity-fp32.json BEHAVIOR_CONFIG={stage["config"]} BEHAVIOR_OUTPUT=runs/fresh-shard-{shard} EPISODE_SHARD_INDEX={shard} EPISODE_SHARD_COUNT=4 timeout --kill-after=60 {remaining} /workspace/jlens-venv/bin/python -u /workspace/jlens-research/scripts/behavior_pilot.py > /workspace/jlens-research/runs/fresh-shard-{shard}/console.log 2>&1 </dev/null &'
        remote(state,command);write(marker,{'at':now.isoformat(),'pod_id':state['pod']['id'],'configuration_sha256':stage['configuration_sha256'],'remaining_timeout':remaining})
    dest=ROOT/'runs/fresh';dest.mkdir(parents=True,exist_ok=True)
    endpoint='root@'+state['pod']['publicIp']+f':/workspace/jlens-research/runs/fresh-shard-{shard}/'
    subprocess.run(['rsync','-rt','--timeout=90','--exclude=/complete.json','--exclude=/progress.json','--exclude=/console.log','--exclude=/error.txt','-e',' '.join(ssh_args(state)),endpoint,str(dest)+'/'],check=True,capture_output=True,timeout=240)
    status=remote(state,f'if test -f /workspace/jlens-research/runs/fresh-shard-{shard}/complete.json; then cat /workspace/jlens-research/runs/fresh-shard-{shard}/complete.json; fi')
    if status.strip():
        complete=json.loads(status);assert complete['configuration_sha256']==stage['configuration_sha256']
        expected=cfg['episodes'][shard::4];assert complete['episodes']==len(expected)
        for ep in expected:
            directory=dest/ep['episode_id'];record=json.loads((directory/'episode.json').read_text());assert record['config_sha256']==stage['configuration_sha256']
            if 'activation_sha256' in record:assert hashlib.sha256((directory/'activations.safetensors').read_bytes()).hexdigest()==record['activation_sha256']
        write(OUT/f'fresh-{shard}-complete.json',complete)
        if not merge_fit64_if_ready():return True
        processed_marker=OUT/f'processed-{shard}-launched.json'
        if not processed_marker.exists():
            for name in ['fit64-merged','fit64-half-a','fit64-half-b']:
                sync(state,ROOT/'runs'/name,'/workspace/jlens-research/runs/',upload=True)
            remote(state,f'mkdir -p /workspace/jlens-research/src /workspace/jlens-research/runs/fresh-processed-{shard} /workspace/jlens-research/runs/readout64-0')
            for name in ['positions.py','source_parser.py']:sync(state,ROOT/'src'/name,'/workspace/jlens-research/src/',upload=True)
            for name in ['postprocess_fresh.py','validate_readouts64.py']:sync(state,ROOT/'scripts'/name,'/workspace/jlens-research/scripts/',upload=True)
            for name in ['jview-interpretation-v1.json','generic-corpus-balanced.json']:sync(state,ROOT/'configs'/name,'/workspace/jlens-research/configs/',upload=True)
            remaining=int((dt.datetime.fromisoformat(state['deadline'])-dt.datetime.now(dt.timezone.utc)).total_seconds())-60
            if remaining<300:return True
            # Generic quality is checked on every worker; all use the same frozen inputs.
            command=f'nohup bash -c "timeout --kill-after=60 600 /workspace/jlens-venv/bin/python -u /workspace/jlens-research/scripts/validate_readouts64.py && timeout --kill-after=60 {max(120,remaining-600)} /workspace/jlens-venv/bin/python -u /workspace/jlens-research/scripts/postprocess_fresh.py --shard {shard}" > /workspace/jlens-research/runs/fresh-processed-{shard}/console.log 2>&1 </dev/null &'
            remote(state,command);write(processed_marker,{'at':now.isoformat(),'pod_id':state['pod']['id']})
        processed=ROOT/f'runs/fresh-processed-{shard}'
        sync(state,f'/workspace/jlens-research/runs/fresh-processed-{shard}/',processed)
        sync(state,'/workspace/jlens-research/runs/readout64-0/',ROOT/f'runs/readout64-worker-{shard}')
        if (processed/'complete.json').exists():
            c=json.loads((processed/'complete.json').read_text());assert c['completed']==len(expected)
            for eid,digest in c['case_complete_sha256'].items():
                case=processed/eid/'complete.json';assert hashlib.sha256(case.read_bytes()).hexdigest()==digest
                for name,sha in json.loads(case.read_text())['files_sha256'].items():assert hashlib.sha256((case.parent/name).read_bytes()).hexdigest()==sha
            write(OUT/f'processed-{shard}-complete.json',c)
            if not advance_challenge(shard,role,path,state):
                stop(role,state,'fresh generation and postprocessing complete; outputs verified',path)
    return True

def tick():
    collect_replay()
    probe=ROOT/'runs/development-probe'
    if all((ROOT/f'runs/replay-{i}/complete.json').exists() for i in range(2)) and not (probe/'complete.json').exists() and not (probe/'failed.json').exists():
        probe.mkdir(parents=True,exist_ok=True)
        with (probe/'console.log').open('a') as log:
            result=subprocess.run(['/workspace/probe-venv/bin/python',str(ROOT/'scripts/fit_development_probe.py')],stdout=log,stderr=log,timeout=300,env={**os.environ,'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','CUDA_VISIBLE_DEVICES':''})
        if result.returncode:write(probe/'failed.json',{'returncode':result.returncode,'reason':'inspect console; no automatic scientific gate relaxation'})
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
                            continuing=stage['name']=='fit64' and advance_fresh(shard,role,path,state)
                            if continuing:row['next_stage']='fresh-v1'
                            else:
                                idle=directory/'controller-completion-seen.json'
                                if not idle.exists():write(idle,{'at':now.isoformat()})
                                elapsed=(now-dt.datetime.fromisoformat(json.loads(idle.read_text())['at'])).total_seconds()
                                if elapsed>=stage.get('warm_idle_grace_seconds',900):
                                    stop(role,state,'stage complete; verified outputs; warm idle grace elapsed',path)
            rows.append(row)
        if stage['name']=='fit64':merge_fit64_if_ready()
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
