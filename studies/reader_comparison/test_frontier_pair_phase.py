import json
import tempfile
import unittest
from pathlib import Path
from audit_frontier_pair_phase import activate_frontier_pair
from smoke import write_json


class FrontierPhaseTest(unittest.TestCase):
    def fixture(self,path):
        data={'status':'paused_after_reader_audit','additional_limit_usd':2,'spent_microusd':450000,'reserved_microusd':3349,'records':{'uncertain':{'status':'reserved','reserved_microusd':3349,'request_sha256':'old'}}}
        write_json(path,data)
        plan={'kind':'bounded-hosted-frontier-pair-qualification-v1','cumulative_limit_usd':5,'request_allowlist':[str(i) for i in range(144)],'maximum_reserved_microusd':3969346,'scope':'test'}
        return data,plan

    def test_explicit_revision_retains_uncertain_charge_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json';prior,plan=self.fixture(path);activate_frontier_pair(path,plan);actual=json.loads(path.read_text())
            for k in ['records','spent_microusd','reserved_microusd']:self.assertEqual(actual[k],prior[k])
            self.assertEqual(actual['additional_limit_usd'],5)
            self.assertEqual(actual['budget_amendments'][0]['previous_limit_usd'],2)
            with self.assertRaisesRegex(ValueError,'Prior coordinator'):activate_frontier_pair(path,plan)

    def test_rejects_unregistered_phase_excess_budget_and_retries_without_mutation(self):
        for change in [{'cumulative_limit_usd':3},{'kind':'production'},{'maximum_reserved_microusd':5000000},{'request_allowlist':['old']+[str(i) for i in range(143)]}]:
            with tempfile.TemporaryDirectory() as tmp,self.subTest(change=change):
                path=Path(tmp)/'ledger.json';_,plan=self.fixture(path);before=path.read_bytes()
                with self.assertRaises(ValueError):activate_frontier_pair(path,{**plan,**change})
                self.assertEqual(path.read_bytes(),before)


