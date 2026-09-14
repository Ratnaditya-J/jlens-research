import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from wasi_sandbox import run

class IsolationTests(unittest.TestCase):
    def execute(self,code,seconds=2):
        with tempfile.TemporaryDirectory(dir=ROOT/'../../work') as temp:
            (Path(temp)/'runner.py').write_text(code)
            return run(temp,seconds=seconds)
    def test_honest_python_runs(self):
        r=self.execute('print(sum([2,3,5]))')
        self.assertEqual(r['status'],'completed');self.assertEqual(r['stdout'],'10\n')
    def test_no_host_files_or_environment(self):
        r=self.execute("import os\nassert not os.environ\ntry:\n open('/etc/passwd').read()\nexcept OSError: print('DENIED')\nelse: print('ESCAPE')")
        self.assertEqual(r['stdout'],'DENIED\n')
    def test_runtime_readonly(self):
        r=self.execute("try:\n open('/usr/escape','w').write('bad')\nexcept OSError: print('DENIED')\nelse: print('ESCAPE')")
        self.assertEqual(r['stdout'],'DENIED\n')
    def test_loop_interrupted(self):
        r=self.execute('while True: pass',seconds=.2)
        self.assertEqual(r['status'],'trap');self.assertLess(r['seconds'],3)
    def test_exit_is_observable(self):
        r=self.execute("import os\nprint('BEFORE',flush=True)\nos._exit(0)\nprint('AFTER')")
        self.assertEqual(r['stdout'],'BEFORE\n');self.assertNotIn('AFTER',r['stdout'])

if __name__=='__main__':unittest.main()
