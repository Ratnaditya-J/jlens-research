import json
import tempfile
import unittest
from pathlib import Path
from complete_primary_validation_reviews import activate,KIND,JOBS_SHA
from smoke import write_json


class RemainingReviewBudgetTests(unittest.TestCase):
    def test_bounded_batch_preserves_prior_costs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ledger.json';old={'status':'paused_after_reader_audit','additional_limit_usd':5,'spent_microusd':2500000,'reserved_microusd':581365,'records':{'unknown':{'status':'reserved','reserved_microusd':581365,'request_sha256':'old'}}};write_json(p,old)
            plan={'kind':KIND,'jobs_sha256':JOBS_SHA,'request_allowlist':['new'],'maximum_reserved_microusd':30000,'scope':'test'}
            activate(p,plan);new=json.loads(p.read_text())
            for k in ['records','spent_microusd','reserved_microusd','additional_limit_usd']:self.assertEqual(old[k],new[k])
    def test_budget_exhaustion_or_retry_never_activates(self):
        for keys,amount in [(['new'],2000000),(['old'],30000),([str(i) for i in range(33)],30000)]:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'ledger.json';write_json(p,{'status':'paused','additional_limit_usd':5,'spent_microusd':3000000,'reserved_microusd':581365,'records':{'unknown':{'status':'reserved','reserved_microusd':581365,'request_sha256':'old'}}});before=p.read_bytes()
                with self.assertRaises(ValueError):activate(p,{'kind':KIND,'jobs_sha256':JOBS_SHA,'request_allowlist':keys,'maximum_reserved_microusd':amount,'scope':'test'})
                self.assertEqual(before,p.read_bytes())
