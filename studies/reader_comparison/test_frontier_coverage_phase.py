import json
import tempfile
import unittest
from pathlib import Path
from audit_frontier_coverage_phase import activate_coverage_budget
from smoke import write_json


class FrontierCoveragePhaseTest(unittest.TestCase):
    def fixture(self,path):
        ledger={'status':'paused_after_reader_audit','additional_limit_usd':5,'spent_microusd':1000000,'reserved_microusd':3349,'records':{'old':{'request_sha256':'old','status':'reserved','reserved_microusd':3349}}}
        plan={'kind':'bounded-hosted-frontier-coverage-v1','request_allowlist':[str(i) for i in range(90)],'jobs_sha256':'ca9bc458bfc298a2c649c5de0e4bd0288fbe85c78de6a63f13bd88cbf7d8c441','maximum_reserved_microusd':3000000,'scope':'test'}
        write_json(path,ledger)
        return ledger,plan

    def test_retains_all_charges_and_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json';old,plan=self.fixture(path)
            activate_coverage_budget(path,plan);new=json.loads(path.read_text())
            for k in ['records','spent_microusd','reserved_microusd','additional_limit_usd']:
                self.assertEqual(new[k],old[k])
            self.assertEqual(new['status'],'active')
            with self.assertRaises(ValueError):activate_coverage_budget(path,plan)

    def test_rejects_wrong_cohort_retry_or_excess_without_mutation(self):
        for change in [{'kind':'production'},{'jobs_sha256':'other'},{'request_allowlist':['old']+[str(i) for i in range(89)]},{'maximum_reserved_microusd':4000000},{'request_allowlist':['same']*90}]:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'ledger.json';_,plan=self.fixture(path);before=path.read_bytes()
                with self.assertRaises(ValueError):activate_coverage_budget(path,{**plan,**change})
                self.assertEqual(path.read_bytes(),before)

    def test_never_increases_previous_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json';old,plan=self.fixture(path);old['additional_limit_usd']=2;write_json(path,old)
            before=path.read_bytes()
            with self.assertRaises(ValueError):activate_coverage_budget(path,plan)
            self.assertEqual(path.read_bytes(),before)
