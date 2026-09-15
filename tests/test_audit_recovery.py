import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import review_batch

class Recovery(unittest.TestCase):
    def fixture(self,root):
        d=root/'runs/fresh/example';d.mkdir(parents=True)
        (root/'scripts').mkdir();(root/'scripts/audit_episode.py').write_text('# fixture')
        (root/'scripts/wasi_sandbox.py').write_text('# sandbox fixture')
        (d/'activations.safetensors').write_bytes(b'fixture')
        ep=d/'episode.json';ep.write_text(json.dumps({'activation_sha256':hashlib.sha256(b'fixture').hexdigest()}))
        return ep
    def check(self,outcome):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);ep=self.fixture(root)
            kwargs={'side_effect':outcome} if isinstance(outcome,Exception) else {'return_value':outcome}
            with patch.object(review_batch,'ROOT',root),patch.object(review_batch.subprocess,'run',**kwargs):
                row=review_batch.process(ep)
            self.assertEqual(row['status'],'audit_error');self.assertNotIn('label',row)
            evidence=json.loads((root/row['failure_artifact']).read_text())
            self.assertEqual(evidence['episode_sha256'],hashlib.sha256(ep.read_bytes()).hexdigest())
            self.assertFalse(ep.with_name('external-audit.json').exists())
            return evidence
    def test_full_crash_diagnostic_retained(self):
        e=self.check(subprocess.CompletedProcess([], -6, 'partial output', 'diagnostic'*100))
        self.assertEqual(e['stderr'],'diagnostic'*100);self.assertEqual(e['returncode'],-6)
    def test_timeout_remains_retryable_failure(self):
        e=self.check(subprocess.TimeoutExpired([],40,output=b'partial',stderr=b'timeout'))
        self.assertEqual(e['timeout_seconds'],40);self.assertEqual(e['stdout'],'partial')

if __name__=='__main__':unittest.main()
