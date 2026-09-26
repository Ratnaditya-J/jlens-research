import json
import tempfile
import unittest
from pathlib import Path
from audit_reference_phase import activate_reference_phase
from smoke import write_json


class ReferencePhaseTest(unittest.TestCase):
    def fixture(self,path):
        data={'status':'paused_after_reader_audit','additional_limit_usd':5,'spent_microusd':450000,'reserved_microusd':3349,'records':{'uncertain':{'status':'reserved','reserved_microusd':3349,'request_sha256':'old'}}}
        write_json(path,data)
        plan={'kind':'bounded-hosted-gpt41reference-qualification-v1','cumulative_limit_usd':5,'request_allowlist':[str(i) for i in range(72)],'maximum_reserved_microusd':2808760,'scope':'test'}
        return data,plan

    def test_explicit_revision_retains_uncertain_charge_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json';prior,plan=self.fixture(path);activate_reference_phase(path,plan);actual=json.loads(path.read_text())
            for k in ['records','spent_microusd','reserved_microusd']:self.assertEqual(actual[k],prior[k])
            self.assertEqual(actual['additional_limit_usd'],5)
            self.assertEqual(actual['budget_amendments'][0]['previous_limit_usd'],5)
            with self.assertRaisesRegex(ValueError,'Prior coordinator'):activate_reference_phase(path,plan)

    def test_rejects_unregistered_phase_excess_budget_and_retries_without_mutation(self):
        for change in [{'cumulative_limit_usd':3},{'kind':'production'},{'maximum_reserved_microusd':5000000},{'request_allowlist':['old']+[str(i) for i in range(71)]}]:
            with tempfile.TemporaryDirectory() as tmp,self.subTest(change=change):
                path=Path(tmp)/'ledger.json';_,plan=self.fixture(path);before=path.read_bytes()
                with self.assertRaises(ValueError):activate_reference_phase(path,{**plan,**change})
                self.assertEqual(path.read_bytes(),before)


