"""Join all reviewed monitor shards, preserving missing labels explicitly."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];cfg=json.loads((ROOT/'configs/monitor-controls-v1.json').read_text());out=ROOT/'runs/monitor-controls';out.mkdir(exist_ok=True)
assert (ROOT/'runs/monitor-collection-complete.json').exists()
rows=[];inputs={}
for shard in range(4):
 raw=ROOT/f'runs/monitor-controls-shard-{shard}';p=raw/'review-summary.json';inputs[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();summary=json.loads(p.read_text());planned=cfg['episodes'][shard::4];index={r['episode_id']:r for r in summary['rows']};assert set(index)=={e['episode_id'] for e in planned}
 for e in planned:
  eid=e['episode_id'];dest=out/eid;dest.mkdir(exist_ok=True);shutil.copy2(raw/eid/'episode.json',dest/'episode.json');rows.append(index[eid])
(out/'review-summary.json').write_text(json.dumps({'rows':rows,'inputs':inputs,'scope':'All24attempts; unavailable/review_error labels stay missing, never benign'},indent=2)+'\n')
(out/'review-complete.json').write_text(json.dumps({'rows':len(rows),'errors':[r for r in rows if r['status'] in ['review_error','audit_error','wait_for_valid_activation_shard']]},indent=2)+'\n')
print('Joined',len(rows),'monitor audit rows')
