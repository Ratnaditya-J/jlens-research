import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from budgeted_hosted_medium import payload, request_json
from contracts import fingerprint
from hosted_text_reader_medium import execution_manifest


class HostedMediumTest(unittest.TestCase):
    def setup_request(self, root):
        request = payload('judge', {'tokens': ['<|endoftext|>']})
        ledger = root/'ledger.json'
        ledger.write_text(json.dumps({'status': 'active', 'additional_limit_usd': 1,
                                     'active_request_allowlist': [fingerprint(request)], 'records': {}}))
        credential = root/'credential.json'
        credential.write_text(json.dumps({'OPENROUTER_API_KEY': 'test-only'}))
        return request, ledger, credential

    def test_pinned_settings_and_successful_cache_never_rebills(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            request, ledger, credential = self.setup_request(root)
            self.assertEqual(request['max_tokens'], 4096)
            self.assertEqual(request['provider']['max_price'], {'prompt': .05, 'completion': .20})
            self.assertEqual(execution_manifest('gptoss20medium')['max_new_tokens'], 4096)
            self.assertEqual(json.loads(request['messages'][1]['content']), {'tokens': ['<|endoftext|>']})
            raw = {'model': 'openai/gpt-oss-20b', 'provider': 'DeepInfra', 'id': 'mock',
                   'usage': {'cost': .0001}, 'choices': [{'finish_reason': 'stop',
                   'message': {'content': '{"score": 1, "confidence": "high"}'}}]}
            with patch('budgeted_hosted_medium.urllib.request.urlopen', return_value=io.StringIO(json.dumps(raw))) as http:
                first = request_json('gptoss20medium', 'judge', {'tokens': ['<|endoftext|>']}, root/'cache', credential, budget_file=ledger)
                second = request_json('gptoss20medium', 'judge', {'tokens': ['<|endoftext|>']}, root/'cache', credential, budget_file=ledger)
                self.assertEqual(first, second)
                self.assertEqual(http.call_count, 1)
            final = json.loads(ledger.read_text())
            self.assertEqual(final['spent_microusd'], 100)
            self.assertEqual(final['reserved_microusd'], 0)

    def test_unknown_cost_stays_reserved_and_cannot_retry(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _, ledger, credential = self.setup_request(root)
            with patch('budgeted_hosted_medium.urllib.request.urlopen', return_value=io.StringIO('{"usage":{}}')) as http:
                for _ in range(2):
                    with self.assertRaises(RuntimeError):
                        request_json('gptoss20medium', 'judge', {'tokens': ['<|endoftext|>']}, root/'cache', credential, budget_file=ledger)
                self.assertEqual(http.call_count, 1)
            self.assertGreater(json.loads(ledger.read_text())['reserved_microusd'], 0)
            self.assertEqual(len(list((root/'cache').glob('*-raw-*.json'))), 1)


if __name__ == '__main__':
    unittest.main()
