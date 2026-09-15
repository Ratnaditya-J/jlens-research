"""Trusted controller data transfer; only vetted dataset files go to GPU workers."""
import concurrent.futures,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def deploy(i):
 pod=json.loads((ROOT/f'runs/pod-replay-{i}.json').read_text())['pod'];host='root@'+pod['publicIp']
 ssh=['ssh','-i','/workspace/private/pod_ed25519','-o','UserKnownHostsFile=/workspace/private/known_hosts','-p',str(pod['portMappings']['22'])]
 rows=json.loads((ROOT/'runs/development-positions.json').read_text())['rows'][i::2]
 sources=[str(ROOT/'runs/confirmation'/x['episode_id']) for x in rows]
 subprocess.run(['rsync','-rt','--include=*/','--include=episode.json','--include=activations.safetensors','--exclude=*','-e',' '.join(ssh),*sources,host+':/workspace/jlens-research/runs/replay-input/'],check=True)
 subprocess.run(ssh+[host,f'nohup env REPLAY_SHARD={i} bash /workspace/jlens-research/scripts/bootstrap_replay.sh > /workspace/jlens-research/runs/bootstrap-replay.log 2>&1 </dev/null &'],check=True)
 print('launched replay',i,flush=True)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(deploy,[0,1]))
