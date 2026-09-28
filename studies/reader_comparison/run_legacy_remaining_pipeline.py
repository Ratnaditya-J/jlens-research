"""Immediate registered handoffs; one paid coordinator at a time, eight total workers."""
import json,subprocess,sys,time
from pathlib import Path
from smoke import write_json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'runs/reader-comparison/legacy-remaining-pipeline'
def main():
 OUT.mkdir(exist_ok=False)
 paid=['--budget-file',str(ROOT.parent/'reader-runtime/openrouter-budget.json'),'--credential-file',str(ROOT.parent/'private/budgeted-openrouter-credentials.json')]
 stages=[('legacy_remaining_summaries.py',paid),('prepare_legacy_remaining_reviews.py',[]),('legacy_remaining_reviews.py',paid),('audit_legacy_remaining_reviews.py',[])]
 for script,args in stages:
  write_json(OUT/'status.json',{'stage':script,'state':'running','at':time.time()})
  with (OUT/(script+'.log')).open('w') as log:
   result=subprocess.run([sys.executable,str(ROOT/'studies/reader_comparison'/script),*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  if result.returncode:
   write_json(OUT/'status.json',{'stage':script,'state':'failed','returncode':result.returncode,'at':time.time()});raise SystemExit(result.returncode)
 write_json(OUT/'complete.json',{'state':'reviews_evaluation_and_audit_complete','at':time.time(),'remaining':'Interpretation and final report/package integration; not full scientific completion'})
 write_json(OUT/'status.json',{'state':'complete','at':time.time()})
if __name__=='__main__':main()
