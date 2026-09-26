import json
import tempfile
import unittest
from pathlib import Path
from accepted_review_tranche import activate, KIND, JOBS_SHA
from smoke import write_json


class ReviewTrancheBudgetTests(unittest.TestCase):
    def fixture(self,path):
        ledger={'status':'paused_after_reader_audit','additional_limit_usd':5,'spent_microusd':2323005,'reserved_microusd':581365,'records':{'unknown':{'status':'reserved','reserved_microusd':581365,'request_sha256':'old'}}}
        plan={'kind':KIND,'jobs_sha256':JOBS_SHA,'request_allowlist':[str(i) for i in range(64)],'maximum_reserved_microusd':1806242,'scope':'test'}
        write_json(path,ledger)
        return ledger,plan
    def test_retains_every_prior_charge_and_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json';old,plan=self.fixture(path);activate(path,plan)
            new=json.loads(path.read_text())
            for key in ['additional_limit_usd','spent_microusd','reserved_microusd','records']:self.assertEqual(old[key],new[key])
            self.assertEqual(new['status'],'active')
    def test_rejects_wrong_cohort_retry_excess_and_duplicates_without_mutation(self):
        for change in [{'jobs_sha256':'wrong'}, {'request_allowlist':['old']+[str(i) for i in range(63)]}, {'maximum_reserved_microusd':2095631}, {'request_allowlist':['duplicate']*64}]:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'ledger.json';_,plan=self.fixture(path);before=path.read_bytes()
                with self.assertRaises(ValueError):activate(path,{**plan,**change})
                self.assertEqual(before,path.read_bytes())
