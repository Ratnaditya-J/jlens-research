"""Exercise the actual handoff function with isolated filesystem and network fakes."""
import ast,datetime as dt,hashlib,json,tempfile,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Handoff(unittest.TestCase):
 def test_no_duplicate_launch_and_deadline_quality_gates(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);out=root/'runs/controller';out.mkdir(parents=True);(root/'configs').mkdir()
   cfg=root/'configs/challenge.json';cfg.write_text(json.dumps({'episodes':[{'episode_id':'synthetic'}]}))
   (root/'configs/next-specificity-controls.json').write_text(json.dumps({'config':'configs/challenge.json','configuration_sha256':hashlib.sha256(cfg.read_bytes()).hexdigest()}))
   quality=root/'runs/readout64-worker-0/report.json';quality.parent.mkdir();quality.write_text(json.dumps({'shard_readout_stability_passed':False}))
   calls=[]
   def write(p,v):p.write_text(json.dumps(v))
   def remote(state,command):calls.append(command);return ''
   namespace={'ROOT':root,'OUT':out,'json':json,'hashlib':hashlib,'dt':dt,'write':write,'remote':remote,'sync':lambda *a,**k:None,'ssh_args':lambda s:['ssh'],'stop':lambda *a:None,'subprocess':types.SimpleNamespace(run=lambda *a,**k:None)}
   tree=ast.parse((ROOT/'scripts/remote_controller.py').read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='advance_specificity')
   exec(compile(ast.Module(body=[function],type_ignores=[]),'handoff','exec'),namespace)
   advance=namespace['advance_specificity'];state={'deadline':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=2)).isoformat(),'pod':{'id':'synthetic','publicIp':'example.invalid'}}
   self.assertFalse(advance(0,'worker0',root/'pod.json',state));self.assertEqual(calls,[])
   quality.write_text(json.dumps({'shard_readout_stability_passed':True}))
   short={**state,'deadline':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=5)).isoformat()}
   self.assertFalse(advance(0,'worker0',root/'pod.json',short));self.assertEqual(calls,[])
   self.assertTrue(advance(0,'worker0',root/'pod.json',state))
   self.assertTrue(advance(0,'worker0',root/'pod.json',state))
   self.assertEqual(sum(command.startswith('nohup ') for command in calls),1)
   cfg.write_text('{}')
   with self.assertRaises(AssertionError):advance(0,'worker0',root/'pod.json',state)
if __name__=='__main__':unittest.main()
