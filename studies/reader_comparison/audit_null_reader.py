"""Check random-control construction and reader coverage without semantic labels."""
import argparse,json,math
from pathlib import Path
import numpy as np
from safetensors.numpy import load_file
from contracts import fingerprint
from smoke import digest,write_json

def main():
 p=argparse.ArgumentParser();p.add_argument('--controls',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--oracle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 cm=json.loads((a.controls/'manifest.json').read_text());sm=json.loads((a.source/'manifest.json').read_text());om=json.loads((a.oracle/'manifest.json').read_text())
 if cm['source_capture_manifest_sha256']!=fingerprint(sm) or om['capture_manifest_sha256']!=fingerprint(cm):raise ValueError('Control provenance differs')
 results={}
 for path in sorted(a.oracle.glob('batch-*.json')):
  batch=json.loads(path.read_text())
  if batch['request']['manifest_sha256']!=fingerprint(om) or batch['request_sha256']!=fingerprint(batch['request']):raise ValueError('Oracle batch changed')
  for r in batch['results']:
   if r['cell_id'] in results:raise ValueError('Duplicate reader cell')
   results[r['cell_id']]=r
 rows=[]
 for path in sorted(a.controls.glob('*/complete.json')):
  done=json.loads(path.read_text());d=path.parent;original=a.source/d.name;source_done=json.loads((original/'complete.json').read_text())
  for directory,complete,manifest in [(d,done,cm),(original,source_done,sm)]:
   if complete['manifest_sha256']!=fingerprint(manifest) or complete['state_sha256']!=digest(directory/'states.safetensors') or complete['cells_sha256']!=digest(directory/'cells.json'):raise ValueError('Corrupt capture')
  z=load_file(d/'states.safetensors');h=load_file(original/'states.safetensors');source_cells={r['state_key']:r for r in json.loads((original/'cells.json').read_text())}
  for cell in json.loads((d/'cells.json').read_text()):
   key=cell['state_key'];source=source_cells[key]
   if source['split']!='train' or cell['source_state_sha256']!=source['state_sha256']:raise ValueError('Control not derived from registered training state')
   x=z[key].astype(np.float64).ravel();y=h[key].astype(np.float64).ravel()
   if not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Nonfinite control or source state')
   nx=math.sqrt(math.fsum(float(v)*float(v) for v in x));ny=math.sqrt(math.fsum(float(v)*float(v) for v in y))
   if not nx or not ny:raise ValueError('Zero-norm state')
   ratio=nx/ny;cos=math.fsum(float(v)*float(w) for v,w in zip(x,y))/(nx*ny);r=results.get(cell['cell_id'])
   if r and r['state_sha256']!=cell['state_sha256']:raise ValueError('Reader consumed wrong control')
   rows.append({'cell_id':cell['cell_id'],'layer':cell['layer'],'norm_ratio':ratio,'cosine_with_source':cos,'status':r['status'] if r else 'unavailable','nonempty_text':bool(r and r['text'].strip()),'truncated':r['truncated'] if r else None,'text':r['text'] if r else None})
 if not rows or max(abs(r['norm_ratio']-1) for r in rows)>1e-5:raise ValueError('Norm matching failed')
 report={'control_manifest_sha256':fingerprint(cm),'oracle_manifest_sha256':fingerprint(om),'n':len(rows),'nonempty_n':sum(r['nonempty_text'] for r in rows),'ok_n':sum(r['status']=='ok' for r in rows),'truncated_n':sum(r['truncated'] is True for r in rows),'rows':rows,'scope':'Norm-matched isotropic directions are out-of-distribution controls, not meaningful model states. Nonempty descriptions demonstrate that fluency is not a fidelity certificate. This is not a natural-state hallucination-rate estimate or evidence of subject intent. No semantic or behavioral labels assigned.'}
 write_json(a.out,report);print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
if __name__=='__main__':main()
