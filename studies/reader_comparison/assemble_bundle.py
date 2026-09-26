"""Build outcome-free interpreter bundles from integrity-checked same-state readouts."""
import argparse,json
from pathlib import Path
from contracts import fingerprint
from smoke import write_json,digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--captures',type=Path,required=True);p.add_argument('--jlens',type=Path,required=True);p.add_argument('--oracle',type=Path,required=True);p.add_argument('--endpoint',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();cm=json.loads((a.captures/'manifest.json').read_text());jm=json.loads((a.jlens/'manifest.json').read_text());om=json.loads((a.oracle/'manifest.json').read_text())
 if cm['identity']!=jm['identity'] or cm['identity']!=om['subject_identity'] or fingerprint(cm)!=jm['capture_manifest_sha256'] or fingerprint(cm)!=om['capture_manifest_sha256']:raise ValueError('Subject/state provenance differs')
 if jm['endpoint']!=a.endpoint or om['endpoint']!=a.endpoint:raise ValueError('Endpoint mismatch')
 oracle={}
 for path in sorted(a.oracle.glob('batch-*.json')):
  batch=json.loads(path.read_text())
  if batch['request']['manifest_sha256']!=fingerprint(om) or batch['request_sha256']!=fingerprint(batch['request']):raise ValueError('Oracle provenance mismatch')
  for r in batch['results']:
   for alias in r.get('alias_cell_ids',[r['cell_id']]):
    if alias in oracle:raise ValueError('Duplicate Oracle cell')
    oracle[alias]=r
 rows=[]
 for path in sorted(a.captures.glob('*/complete.json')):
  directory=path.parent;done=json.loads(path.read_text());eid=directory.name
  if done['cells_sha256']!=digest(directory/'cells.json'):raise ValueError('Cell metadata changed')
  cells=[r for r in json.loads((directory/'cells.json').read_text()) if r['endpoint']==a.endpoint];jd=a.jlens/eid;jdone=json.loads((jd/'complete.json').read_text())
  if jdone['manifest_sha256']!=fingerprint(jm) or jdone['readouts_sha256']!=digest(jd/'readouts.json'):raise ValueError('J-readout provenance mismatch')
  jrows={r['cell_id']:r for r in json.loads((jd/'readouts.json').read_text())};prefixes={fingerprint(r['prefix_ids']) for r in cells}
  if len(prefixes)!=1:raise ValueError('Layers have different prefixes')
  output={'episode_id':eid,'family_id':cells[0]['family_id'],'split':cells[0]['split'],'prefix_sha256':next(iter(prefixes)),'prefix_text':cells[0]['prefix_text'],'endpoint':a.endpoint,'position_in_generated_output':cells[0]['position_in_generated_output'],'j_tokens':[],'oracle':[]}
  for cell in cells:
   j=jrows[cell['cell_id']];o=oracle.get(cell['cell_id'])
   if j['state_sha256']!=cell['state_sha256'] or (o and o['state_sha256']!=cell['state_sha256']):raise ValueError('Methods used different residuals')
   native=j['readouts']['native'];output['j_tokens'].append({'layer':cell['layer'],'tokens':native['tokens'][:10],'scores':native['scores'][:10],'token_ids':native['token_ids'][:10]});output['oracle'].append({'layer':cell['layer'],'status':o['status'] if o else 'unavailable','text':o['text'] if o else '', 'truncated':o['truncated'] if o else None})
  rows.append(output)
 write_json(a.out,{'subject_identity':cm['identity'],'endpoint':a.endpoint,'capture_manifest_sha256':fingerprint(cm),'jlens_manifest_sha256':fingerprint(jm),'lens_n_prompts':jm['n_fit_prompts'],'lens_sha256':jm['lens_sha256'],'oracle_manifest_sha256':fingerprint(om),'scope':'No labels, action outcomes, future text, or detector scores included','rows':rows});print(json.dumps({'rows':len(rows)}),flush=True)
if __name__=='__main__':main()
