import json
import tempfile
import unittest
from pathlib import Path
from audit_budgeted_reader import activate_budget, pause_budget
from budgeted_api_client import reserve, settle
from smoke import write_json


class AuditBudgetTests(unittest.TestCase):
    def test_audit_reduces_ceiling_and_repauses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'budget.json'
            write_json(path, {'status': 'paused_for_cost_control', 'additional_limit_usd': 10, 'records': {}})
            activate_budget(path, 'fixture')
            self.assertEqual(json.loads(path.read_text())['additional_limit_usd'], 1)
            token = reserve(path, .8, 'request')
            with self.assertRaises(RuntimeError):
                reserve(path, .3, 'other')
            settle(path, token, .1, 'response')
            ledger = pause_budget(path)
            self.assertEqual(ledger['status'], 'paused_after_reader_audit')
            with self.assertRaises(RuntimeError):
                reserve(path, .1, 'blocked')
            with self.assertRaises(ValueError):
                activate_budget(path, 'cannot_silently_restart')

    def test_unexpected_charge_remains_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'budget.json'
            write_json(path, {'status': 'paused_for_cost_control', 'additional_limit_usd': 10, 'records': {}})
            activate_budget(path, 'fixture')
            token = reserve(path, .1, 'request')
            with self.assertRaises(RuntimeError):
                settle(path, token, .2, 'response')
            self.assertEqual(pause_budget(path)['status'], 'paused_unexpected_charge')


if __name__ == '__main__':
    unittest.main()
