import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from parallel_hosted_jobs import run_wave
from budgeted_api_client import reserve
from smoke import write_json

class ParallelTests(unittest.TestCase):
    def test_eight_simultaneous_isolated_invocations(self):
        barrier=threading.Barrier(8)
        paths=[];lock=threading.Lock()
        def runner(candidate,jobs,out,credential,budget):
            with lock:paths.append(str(out))
            barrier.wait(timeout=5)
            out.mkdir();write_json(out/'done.json',{'jobs':json.loads(jobs.read_text())})
        with tempfile.TemporaryDirectory() as d:
            jobs=[{'request_id':str(i)} for i in range(8)]
            done=run_wave('test',jobs,runner,Path(d)/'wave',None,None)
            self.assertEqual(len(done),8);self.assertEqual(len(set(paths)),8)
            for j,p in done:self.assertEqual(json.loads((p/'done.json').read_text())['jobs']['jobs'],[j])
    def test_concurrent_budget_reservations_cannot_overspend(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'budget.json';keys=[str(i) for i in range(8)]
            write_json(p,{'status':'active','additional_limit_usd':.1,'records':{},'active_request_allowlist':keys})
            barrier=threading.Barrier(8)
            def attempt(key):
                barrier.wait(timeout=5)
                try:return reserve(p,.02,key)
                except RuntimeError:return None
            with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(attempt,keys))
            self.assertEqual(sum(x is not None for x in results),5)
            b=json.loads(p.read_text());self.assertEqual(b['reserved_microusd'],100000)
            self.assertEqual(len(b['records']),5)
            key=next(iter(b['records'].values()))['request_sha256']
            with self.assertRaises(RuntimeError):reserve(p,.02,key)
    def test_rejects_duplicate_and_unbounded_wave(self):
        with tempfile.TemporaryDirectory() as d:
            for jobs in [[{'request_id':'same'}]*2,[{'request_id':str(i)} for i in range(9)]]:
                with self.assertRaises(ValueError):run_wave('test',jobs,None,Path(d)/'wave',None,None)

if __name__=='__main__':unittest.main()
