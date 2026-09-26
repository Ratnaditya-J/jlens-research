"""Freeze selected detectors and validation-only reader thresholds."""
import argparse,json
from pathlib import Path
import numpy as np
from contracts import conservative_threshold,fingerprint
from smoke import write_json,digest
from interpret_readers import ARMS

def main():
 p=argparse.ArgumentParser();p.add_argument('--features',type=Path,required=True);p.add_argument('--probes',type=Path,required=True);p.add_argument('--interpretations',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--text-baseline',type=Path,required=True);a=p.parse_args();manifest=json.loads((a.features/'manifest.json').read_text());cfgpath=Path(__file__).parent/'comparison_config.json';cfg=json.loads(cfgpath.read_text());scorepath=a.interpretations/'scores.json';complete=json.loads((a.interpretations/'complete.json').read_text());im=json.loads((a.interpretations/'manifest.json').read_text())
 if complete['manifest_sha256']!=fingerprint(im):raise ValueError('Changed validation interpretation manifest')
 if complete['scores_sha256']!=digest(scorepath) or im['phase']!='validation' or im['subject_identity']!=manifest['identity']:raise ValueError('Wrong reader phase or changed scores')
 if manifest['lens_n_prompts']!=cfg['primary_lens_prompts'] or im['lens_n_prompts']!=cfg['primary_lens_prompts'] or im['lens_sha256']!=manifest['lens_sha256']:raise ValueError('Primary lens fit differs from registration')
 if digest(a.features/'features.npz')!=manifest['feature_sha256']:raise ValueError('Feature corruption')
 score={r['episode_id']:r for r in json.loads(scorepath.read_text())};episodes={r['episode_id']:r for r in manifest['rows'] if r['split']=='validation' and r['condition']=='prohibited'};thresholds={};arms={}
 for arm in ARMS:
  negatives=[score[e][arm]['score'] for e,r in episodes.items() if r['label']==0 and e in score and score[e][arm]['score'] is not None];threshold=conservative_threshold(negatives,cfg['target_validation_fpr']);thresholds[arm]=threshold;arms[arm]={'validation_benign_n':len(negatives),'validation_fpr':sum(s>=threshold for s in negatives)/len(negatives)}
 for arm in ['raw','jspace']:
  pr=json.loads((a.probes/(arm+'-probe.json')).read_text())
  if pr['identity']!=manifest['identity'] or pr['feature_manifest_sha256']!=fingerprint(manifest) or pr['endpoint']!=im['endpoint']:raise ValueError('Wrong probe/capture/endpoint provenance')
  thresholds[arm+'_probe']=pr['threshold'];arms[arm+'_probe']={'selected_layer':pr['selected']['layer'],'selected_C':pr['selected']['C'],'validation_benign_n':pr['validation_benign_n'],'validation_fpr':pr['validation_false_positives']/pr['validation_benign_n']}
 arrays=np.load(a.features/'features.npz',allow_pickle=False);raw=json.loads((a.probes/'raw-probe.json').read_text());weights=np.asarray(raw['weights']);raw_validation={}
 for i,r in enumerate(manifest['rows']):
  if r['split']=='validation' and r['condition']=='prohibited' and r['label']==0 and r['layer']==raw['selected']['layer']:
   value=float(np.einsum('i,i->',arrays['X_raw'][i].astype(np.float64),weights)+raw['intercept'])
   if not np.isfinite(value):raise ValueError('Nonfinite validation probe score')
   raw_validation[r['episode_id']]=value
 for arm in ARMS:
  paired=[v for eid,v in raw_validation.items() if eid in score and score[eid][arm]['score'] is not None]
  arms[arm]['matched_raw_probe_threshold']=conservative_threshold(paired,arms[arm]['validation_fpr']);arms[arm]['matched_raw_probe_validation_n']=len(paired)
 text=json.loads((a.text_baseline/'lock.json').read_text())
 if text['identity']!=manifest['identity'] or text['endpoint']!=pr['endpoint'] or text['capture_manifest_sha256']!=manifest['capture_manifest_sha256'] or digest(a.text_baseline/'model.joblib')!=text['model_sha256']:raise ValueError('Wrong text baseline provenance')
 thresholds['text_probe']=text['threshold'];arms['text_probe']={'selected_C':text['selected']['C'],'validation_benign_n':text['validation_benign_n'],'validation_fpr':text['validation_false_positives']/text['validation_benign_n']}
 sources=[a.text_baseline/'lock.json',a.text_baseline/'model.joblib',cfgpath,a.features/'manifest.json',a.features/'features.npz',a.probes/'raw-probe.json',a.probes/'jspace-probe.json',scorepath,a.interpretations/'manifest.json',Path(__file__),Path(__file__).parent/'interpret_readers.py',Path(__file__).parent/'api_client.py',Path(__file__).parent/'probes.py']
 lock={'identity':manifest['identity'],'endpoint':pr['endpoint'],'thresholds':thresholds,'arms':arms,'source_hashes':{str(p.resolve()):digest(p) for p in sources},'interpreter_code_sha256':digest(Path(__file__).parent/'interpret_readers.py'),'scope':'Train-selected detectors, validation-only thresholds; no test performance accessed'}
 a.out.mkdir(parents=True,exist_ok=True)
 if (a.out/'lock.json').exists():raise ValueError('Calibration already locked')
 write_json(a.out/'lock.json',lock);print(json.dumps({'thresholds':thresholds,'arms':arms}),flush=True)
if __name__=='__main__':main()
