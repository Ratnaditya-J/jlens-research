import hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StageCLI(unittest.TestCase):
 def test_dry_run_resume_and_changed_artifacts(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'scripts').mkdir();(root/'configs').mkdir()
   shutil.copy(ROOT/'scripts/study.py',root/'scripts/study.py')
   script=root/'scripts/evaluate_fresh.py'
   script.write_text("from pathlib import Path\np=Path('count.txt')\np.write_text(str(int(p.read_text())+1) if p.exists() else '1')\n")
   identity=root/'configs/identity.json';identity.write_text(json.dumps({k:{'repo':'synthetic','revision':'a'*40} for k in ['base','adapter']}))
   cfg={'stage':'compare','identity_config':'configs/identity.json','inputs_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [script,identity]},'commands':[{'script':'evaluate_fresh.py'}],'outputs':['count.txt'],'resource_estimate':{'gpu_hours':0},'scope':'synthetic CLI test only'}
   config=root/'configs/stage.json';config.write_text(json.dumps(cfg))
   def run(*extra):return subprocess.run([sys.executable,str(root/'scripts/study.py'),'compare','--config',str(config),*extra],capture_output=True,text=True)
   dry=run();self.assertEqual(dry.returncode,0,dry.stderr);self.assertFalse((root/'count.txt').exists())
   first=run('--execute');self.assertEqual(first.returncode,0,first.stderr)
   again=run('--execute');self.assertEqual(again.returncode,0,again.stderr);self.assertEqual((root/'count.txt').read_text(),'1');self.assertIn('already_complete_verified',again.stdout)
   (root/'count.txt').write_text('changed');self.assertNotEqual(run('--execute').returncode,0)
   script.write_text(script.read_text()+'# changed\n');self.assertNotEqual(run().returncode,0)
if __name__=='__main__':unittest.main()
