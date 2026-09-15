"""Reconstruct completed native-model control analysis in a fresh input-only venv."""
import argparse,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True);a=p.parse_args();dest=a.destination.resolve();assert not dest.exists() and not ROOT.is_relative_to(dest)
 summary=ROOT/'reports/model-controls/summary.json';analysis=json.loads(summary.read_text());expected={n:sha(ROOT/n) for n in ['reports/model-controls/summary.json','reports/model-controls/findings.md']};inputs=dict(analysis['inputs']);inputs['scripts/analyze_model_controls.py']=sha(ROOT/'scripts/analyze_model_controls.py')
 dest.mkdir(parents=True);replica=dest/'repository';replica.mkdir();started=time.time();report={'status':'running','scope':'Fresh standard-library-only Python environment; copied frozen behavioral labels/configs/collection markers. No API calls, GPU, new labels or generation.','inputs_sha256':inputs,'expected_outputs_sha256':expected,'script_sha256':sha(Path(__file__))}
 try:
  for n,h in inputs.items():
   source=ROOT/n;assert sha(source)==h;target=replica/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
  (replica/'reports').mkdir(exist_ok=True)
  subprocess.run([sys.executable,'-m','venv',str(dest/'venv')],check=True)
  python=dest/'venv/bin/python'
  for attempt in range(2):
   with (dest/f'reconstruct-{attempt}.log').open('w') as log:subprocess.run([str(python),'scripts/analyze_model_controls.py'],cwd=replica,stdout=log,stderr=log,check=True)
   assert all(sha(replica/n)==h for n,h in expected.items())
  assert all(sha(ROOT/n)==h for n,h in {**inputs,**expected}.items())
  report.update(status='passed',reproduced_outputs_sha256={n:sha(replica/n) for n in expected},exact_outputs=len(expected),elapsed_seconds=time.time()-started)
 except Exception as error:
  report.update(status='failed',error=repr(error));raise
 finally:(ROOT/'reports/model-controls-reproduction.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'exact_outputs':report.get('exact_outputs'),'elapsed_seconds':report.get('elapsed_seconds')}))
if __name__=='__main__':main()
