"""Bounded local continuation of registered summary stages; no threshold overwrites."""
import argparse,concurrent.futures,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def wait_file(path,timeout=10800):
 start=time.time()
 while not path.exists():
  if time.time()-start>timeout:raise TimeoutError(str(path))
  time.sleep(15)
def main():
 p=argparse.ArgumentParser();p.add_argument('--credential-file',type=Path,required=True);a=p.parse_args();scientific=str(ROOT.parent/'jlens-review-venv/bin/python');credential=['--credential-file',str(a.credential_file)]
 def run(script,args,log,science=False):
  with (ROOT/'runs'/log).open('w') as f:subprocess.run([scientific if science else sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
 def endpoint(offset):
  suffix=f'-offset{offset}' if offset else '';args=['--offset',str(offset)]
  if offset in [0,32]:
   wait_file(ROOT/f'runs/fresh{suffix}-jsummary-validation/review-complete.json')
   if not (ROOT/f'runs/fresh{suffix}-jsummary-calibration/lock.json').exists():run('calibrate_jsummary.py',args,f'jsummary-calibration-{offset}.log',True)
   run('summarize_jviews.py',['--phase','test',*args,*credential],f'jsummary-test-{offset}.log')
   run('interpret_jsummary.py',['--phase','test',*args,*credential],f'jsummary-review-test-{offset}.log')
  else:wait_file(ROOT/f'runs/fresh{suffix}-jsummary-test/review-complete.json')
  run('evaluate_jsummary.py',args,f'jsummary-evaluate-{offset}.log',True)
  print(json.dumps({'completed_endpoint':offset}),flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(endpoint,[0,32,64]))
 for dataset in ['template-challenge','specificity-controls','monitor-controls']:
  source=ROOT/f'runs/{dataset}-assembled/test-readouts.json'
  if not source.exists():raise FileNotFoundError(str(source))
  args=['--offset','0','--dataset',dataset]
  run('summarize_jviews.py',['--phase','test',*args,*credential],f'jsummary-{dataset}-summary.log')
  run('interpret_jsummary.py',['--phase','test',*args,*credential],f'jsummary-{dataset}-review.log')
  run('evaluate_jsummary.py',args,f'jsummary-{dataset}-evaluate.log',True)
  print(json.dumps({'completed_control':dataset}),flush=True)
if __name__=='__main__':main()
