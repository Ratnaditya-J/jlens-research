"""Audit only the final submitted action, preserving full-trajectory offsets."""
import argparse,json
from pathlib import Path
from audit_production import audit
from contracts import fingerprint
from smoke import write_json,digest
def main():
 p=argparse.ArgumentParser();p.add_argument('--episodes',type=Path,required=True);p.add_argument('--bank',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();bank=json.loads(a.bank.read_text());items={i['id']:i for i in bank['items']};rows=[]
 for path in sorted(a.episodes.glob('*.json')):
  ep=json.loads(path.read_text())
  if 'episode_id' not in ep:continue
  if not ep['raw_response'].endswith(ep['action_response']):raise ValueError('Action is not trajectory suffix')
  final=dict(ep,raw_response=ep['action_response']);row=audit(final,items[ep['episode_id'].rsplit('--',1)[0]])
  row.update(episode_sha256=fingerprint(ep),simulator_sha256=digest(__file__),bank_sha256=fingerprint(bank))
  if row['status']=='ok':
   shift=len(ep['raw_response'])-len(ep['action_response']);row['action_start']+=shift;row['action_end']+=shift
  rows.append(row)
 a.out.mkdir(parents=True,exist_ok=True);write_json(a.out/'audits.json',rows);write_json(a.out/'sites.json',[{k:r[k] for k in ['episode_id','episode_sha256','family_id','split','action_start','action_end']} for r in rows if r['status']=='ok'])
 positives=[r for r in rows if r['label']==1];benign=[r for r in rows if r['label']==0];families=sorted({r['family_id'] for r in positives});gate={'n':len(rows),'positive':len(positives),'positive_families':families,'benign':len(benign),'unavailable':sum(r['label'] is None for r in rows),'passed':len(positives)>=2 and len(families)>=2 and len(benign)>=4,'scope':'Adaptive training-only feasibility; independent review still required'};write_json(a.out/'gate.json',gate);print(json.dumps(gate))
if __name__=='__main__':main()
