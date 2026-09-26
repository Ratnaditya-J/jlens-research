import json
import tempfile
import unittest
from pathlib import Path
from accepted_summary_batch import activate,KIND,JOBS_SHA
from smoke import write_json


class AcceptedSummaryBudgetTest(unittest.TestCase):
    def fixture(self,path):
        ledger={'status':'paused_after_reader_audit','additional_limit_usd':5,'spent_microusd':2500000,'reserved_microusd':581365,'records':{'old':{'status':'reserved','reserved_microusd':581365,'request_sha256':'old'}}}
        write_json(path,ledger)
        return ledger,{'kind':KIND,'jobs_sha256':JOBS_SHA,'request_allowlist':[str(i) for i in range(64)],'maximum_reserved_microusd':1268043,'scope':'test'}
    def test_preserves_cap_and_unknown_charges(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json';old,plan=self.fixture(p);activate(p,plan);new=json.loads(p.read_text())
            for k in ['additional_limit_usd','spent_microusd','reserved_microusd','records']:self.assertEqual(new[k],old[k])
            self.assertEqual(new['status'],'active')
    def test_wrong_cohort_retry_and_unaffordable_batch_do_not_mutate(self):
        for change in [{'jobs_sha256':'other'},{'request_allowlist':['old']+[str(i) for i in range(63)]},{'maximum_reserved_microusd':2000000}]:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'ledger.json';_,plan=self.fixture(p);before=p.read_bytes()
                with self.assertRaises(ValueError):activate(p,{**plan,**change})
                self.assertEqual(p.read_bytes(),before)
