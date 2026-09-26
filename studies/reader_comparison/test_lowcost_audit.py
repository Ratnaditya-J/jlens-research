import json
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audit_lowcost_pair import activate_budget
from budgeted_api_client import lowcost_payload, lowcost_reservation, reserve, settle, request_lowcost_json
from contracts import fingerprint


class LowcostAuditTests(unittest.TestCase):
    def test_transport_failures_retain_provenance_and_block_retries(self):
        cases = [('missing_cost', None, 'DeepInfra', 'stop', RuntimeError),
                 ('wrong_provider', .0001, 'Other', 'stop', ValueError),
                 ('truncated', .0001, 'DeepInfra', 'length', ValueError)]
        for name, cost, provider, finish, error in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                ledger = root/'ledger.json'
                credential = root/'credential.json'
                credential.write_text(json.dumps({'OPENROUTER_API_KEY': 'test-only'}))
                key = fingerprint(lowcost_payload('gptoss120', 'judge', {'x': 1}))
                ledger.write_text(json.dumps({'status': 'active', 'additional_limit_usd': 1,
                    'records': {}, 'active_request_allowlist': [key]}))
                raw = {'model': 'openai/gpt-oss-120b', 'provider': provider,
                       'usage': {'cost': cost}, 'id': 'mock',
                       'choices': [{'finish_reason': finish, 'message': {'content': '{"score": 1}'}}]}
                with patch('budgeted_api_client.urllib.request.urlopen', return_value=io.StringIO(json.dumps(raw))) as http:
                    with self.assertRaises(error):
                        request_lowcost_json('gptoss120', 'judge', {'x': 1}, root/'cache', credential, budget_file=ledger)
                    with self.assertRaises(RuntimeError):
                        request_lowcost_json('gptoss120', 'judge', {'x': 1}, root/'cache', credential, budget_file=ledger)
                    self.assertEqual(http.call_count, 1)
                final = json.loads(ledger.read_text())
                self.assertEqual(len(list((root/'cache').glob('*-raw-*.json'))), 1)
                self.assertFalse((root/'cache'/(key+'.json')).exists())
                if cost is None:
                    self.assertGreater(final['reserved_microusd'], 0)
                    self.assertEqual(final.get('spent_microusd', 0), 0)
                else:
                    self.assertEqual(final['reserved_microusd'], 0)
                    self.assertEqual(final['spent_microusd'], 100)

    def test_payload_preserves_evidence_and_pins_route_price_and_reasoning(self):
        evidence = {'tokens': ['<|endoftext|>', '[INST]', '☃']}
        for candidate, endpoint, price in [('gptoss120', 'deepinfra/bf16', .3),
                                            ('deepseek32', 'siliconflow/fp8', .5)]:
            p = lowcost_payload(candidate, 'judge only', evidence)
            self.assertEqual(json.loads(p['messages'][1]['content']), evidence)
            self.assertNotIn('<|endoftext|>', p['messages'][1]['content'])
            self.assertEqual(p['provider']['only'], [endpoint])
            self.assertFalse(p['provider']['allow_fallbacks'])
            self.assertEqual(p['provider']['max_price']['completion'], price)
            self.assertEqual(p['reasoning'], {'effort': 'medium'})
            self.assertEqual(p['max_tokens'], 2048)
            self.assertGreater(lowcost_reservation(p), 0)
        with self.assertRaises(KeyError):
            lowcost_payload('premium-unregistered-model', 'judge', evidence)

    def test_allowlist_blocks_other_requests_and_retry_after_settlement(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'ledger.json'
            p.write_text(json.dumps({'status': 'active', 'additional_limit_usd': 1,
                                     'active_request_allowlist': ['allowed'], 'records': {}}))
            with self.assertRaises(RuntimeError):
                reserve(p, .1, 'not-allowed')
            token = reserve(p, .1, 'allowed')
            settle(p, token, .01, 'response')
            with self.assertRaises(RuntimeError):
                reserve(p, .1, 'allowed')

    def test_activation_preserves_spending_and_refuses_insufficient_or_uncertain_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'ledger.json'
            original = {'status': 'paused_after_reader_audit', 'additional_limit_usd': 1,
                        'spent_microusd': 244215, 'reserved_microusd': 0,
                        'records': {'old': {'request_sha256': 'old', 'status': 'settled'}}}
            plan = {'request_allowlist': ['new'], 'maximum_reserved_microusd': 600000}
            p.write_text(json.dumps(original))
            activate_budget(p, plan)
            active = json.loads(p.read_text())
            self.assertEqual(active['spent_microusd'], 244215)
            self.assertEqual(active['additional_limit_usd'], 1)
            self.assertEqual(active['records'], original['records'])
            for override in [{'reserved_microusd': 1}, {'spent_microusd': 500000},
                             {'additional_limit_usd': 10}]:
                p.write_text(json.dumps({**original, **override}))
                before = p.read_bytes()
                with self.assertRaises(ValueError):
                    activate_budget(p, plan)
                self.assertEqual(p.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
