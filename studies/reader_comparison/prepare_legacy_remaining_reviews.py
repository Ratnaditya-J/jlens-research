"""Completion-triggered offline preparation using the frozen review builder AST prefix."""
import ast,json,sys,time
from pathlib import Path
from smoke import digest,write_json
ROOT=Path(__file__).resolve().parents[2]
def main():
 source=ROOT/'scripts/interpret_jsummary.py';tree=ast.parse(source.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
 index=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='results' for t in n.targets))
 fn.body=fn.body[:index]+ast.parse('capture(jobs, manifest)').body
 # No original inference function, executor, main invocation or network transport is executed.
 tree.body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.Assign))]+[fn];ast.fix_missing_locations(tree)
 out=ROOT/'runs/reader-comparison/legacy-remaining-review-preparation'
 if out.exists():raise ValueError('Preserve prior preparation')
 out.mkdir();deadline=time.monotonic()+3600
 while not (ROOT/'runs/reader-comparison/legacy-remaining-summaries/complete.json').exists():
  if time.monotonic()>deadline:raise TimeoutError('Summaries not complete; no paid requests launched')
  time.sleep(1)
 result={}
 for panel in ['template-challenge','fresh-completion']:
  def capture(jobs,manifest):
   result[panel]={'jobs':[{'episode_id':e,'arm':a,'model':m,'system':s,'evidence':v} for e,a,m,s,v in jobs],'manifest':manifest}
  ns={'__file__':str(source),'__name__':'frozen_preparation_only','capture':capture};exec(compile(tree,str(source),'exec'),ns)
  sys.argv=[str(source),'--phase','test','--dataset',panel,'--credential-file','UNUSED_PREPARATION_ONLY'];ns['main']()
  write_json(out/(panel+'.json'),result[panel])
 write_json(out/'complete.json',{'source_hashes':{str(source):digest(source),str(Path(__file__).resolve()):digest(__file__)},'prepared':{k:len(v['jobs']) for k,v in result.items()},'scope':'Exact AST prefix of frozen main ending before inference results initialization. No paid calls or credential reads. Review-manifests created by unchanged builder; sidecars retain jobs for guarded dispatch. Original code/config/calibration unchanged.'})
 print(json.dumps({'prepared':{k:len(v['jobs']) for k,v in result.items()}}),flush=True)
if __name__=='__main__':main()
