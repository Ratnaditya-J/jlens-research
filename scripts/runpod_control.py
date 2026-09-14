"""Local-only RunPod controller. Never transfer this credential boundary to tasks."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]

def api(path, method='GET', body=None):
    key = os.environ.get('RUNPOD_API_KEY')
    if not key:
        content = (Path.home() / '.runpod/config.toml').read_text()
        match = re.search(r'''(?im)^\s*(?:api_key|apikey|apiKey)\s*=\s*["']([^"']+)''', content)
        if not match:
            raise RuntimeError('RunPod credential missing')
        key = match.group(1)
    # Secret passed over stdin, never argv, logs, or saved manifests.
    config = f'url = "https://rest.runpod.io/v1/{path}"\nheader = "Authorization: Bearer {key}"\nheader = "Content-Type: application/json"\nuser-agent = "jlens-research/1.0"\n'
    args = ['curl', '--silent', '--show-error', '--fail-with-body', '--max-time', '45', '--config', '-', '--request', method]
    if body is not None:
        args += ['--data', json.dumps(body)]
    result = subprocess.run(args, input=config, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'RunPod HTTP request failed: {result.stdout[:600].replace(key, "[REDACTED]")}')
    return json.loads(result.stdout) if result.stdout.strip() else {}

def sanitized(pod):
    return {k: pod.get(k) for k in ['id','name','desiredStatus','imageName','gpuCount','gpu','costPerHr','publicIp','portMappings','machine','volumeInGb']}

def main():
    p=argparse.ArgumentParser(); p.add_argument('action', choices=['create','status','stop','terminate','watch']); p.add_argument('--request',type=Path); args=p.parse_args()
    state_path=ROOT/'runs/pod.json'
    if args.action=='create':
        if state_path.exists() and not json.loads(state_path.read_text()).get('terminated'):
            raise RuntimeError('Tracked pod exists; inspect it before creating another')
        public_key=(ROOT/'../../work/private/pod_ed25519.pub').resolve().read_text().strip()
        body={'name':'jlens-identity-pilot','imageName':'runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404','cloudType':'SECURE','computeType':'GPU','gpuCount':1,'gpuTypeIds':['NVIDIA A100-SXM4-80GB','NVIDIA A100 80GB PCIe'],'gpuTypePriority':'availability','containerDiskInGb':30,'volumeInGb':100,'volumeMountPath':'/workspace','ports':['22/tcp'],'env':{'PUBLIC_KEY':public_key},'interruptible':False}
        if args.request:
            body.update(json.loads(args.request.read_text()))
            body['env']={'PUBLIC_KEY':public_key}
        limits=json.loads((ROOT/'configs/resources.json').read_text())
        assert body['gpuCount']<=limits['max_concurrent_gpus']
        if state_path.exists():
            old=json.loads(state_path.read_text())
            (ROOT/'runs'/('pod-'+old['pod']['id']+'.json')).write_text(json.dumps(old,indent=2)+'\n')
        pod=api('pods','POST',body)
        now=dt.datetime.now(dt.timezone.utc)
        state={'pod':sanitized(pod),'created_at':now.isoformat(),'deadline':(now+dt.timedelta(hours=6)).isoformat(),'request':body,'terminated':False}
        state_path.write_text(json.dumps(state,indent=2)+'\n'); print(json.dumps(state['pod']))
        return
    state=json.loads(state_path.read_text()); pod_id=state['pod']['id']
    if args.action=='watch':
        deadline=dt.datetime.fromisoformat(state['deadline'])
        while not state.get('terminated'):
            if dt.datetime.now(dt.timezone.utc)>=deadline:
                try:
                    api(f'pods/{pod_id}/stop','POST')
                    state['stopped_at']=dt.datetime.now(dt.timezone.utc).isoformat()
                    state['stop_reason']='six-hour wall-clock deadline'
                    state_path.write_text(json.dumps(state,indent=2)+'\n')
                    print('Pod stopped at deadline',flush=True); return
                except Exception as e: print(type(e).__name__,str(e),flush=True)
            time.sleep(60)
            state=json.loads(state_path.read_text())
            if state['pod']['id']!=pod_id: return
        return
    if args.action=='status':
        pod=sanitized(api(f'pods/{pod_id}'));state['pod']=pod
        state['last_checked_at']=dt.datetime.now(dt.timezone.utc).isoformat()
        state_path.write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(pod));return
    if args.action=='stop':
        api(f'pods/{pod_id}/stop','POST');state['stopped_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    else:
        api(f'pods/{pod_id}','DELETE');state['terminated']=True;state['terminated_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    state_path.write_text(json.dumps(state,indent=2)+'\n');print(args.action+' complete')

if __name__=='__main__': main()
