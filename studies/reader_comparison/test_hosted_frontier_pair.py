import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from budgeted_hosted_frontier_pair import payload, request_json
from contracts import fingerprint
from hosted_text_reader_frontier_pair import execution_manifest


class HostedFrontierPairTest(unittest.TestCase):
    def fixture(self, root):
        ledger=root/'ledger.json';credential=root/'credential.json'
        credential.write_text(json.dumps({'OPENROUTER_API_KEY':'test-only'}))
        key=fingerprint(payload('gpt54flex','judge',{'x':1}))
        ledger.write_text(json.dumps({'status':'active','additional_limit_usd':1,
            'active_request_allowlist':[key],'records':{}}))
        return ledger,credential

    def test_payload_omits_unsupported_temperature_and_pins_flex(self):
        p=payload('gpt54flex','judge',{'tokens':['<|endoftext|>']})
        self.assertNotIn('temperature',p)
        self.assertNotIn('quantizations',p['provider'])
        self.assertEqual(p['provider']['only'],['openai/flex'])
        self.assertFalse(p['provider']['allow_fallbacks'])
        self.assertEqual(p['seed'],20260926)
        self.assertEqual(p['max_tokens'],2048)
        self.assertEqual(execution_manifest('gpt54flex')['model']['family'],'gpt5')
        self.assertEqual(json.loads(p['messages'][1]['content']),{'tokens':['<|endoftext|>']})

    def test_manifest_verification_rejects_configuration_and_source_changes(self):
        from collect_local_readers import execution_source
        import copy
        for candidate in ['gpt54flex','deepseek32atlas']:
            original=execution_manifest(candidate)
            self.assertEqual(execution_source(original).name,'hosted_text_reader_frontier_pair.py')
            for key in ['transport_code_sha256','decoder_code_sha256','budget_guard_code_sha256']:
                changed=copy.deepcopy(original);changed[key]='changed'
                with self.assertRaises(ValueError):execution_source(changed)
            changed=copy.deepcopy(original);changed['model']['endpoint']='unregistered'
            with self.assertRaises(ValueError):execution_source(changed)

    def test_alternate_route_is_separate_and_fp8(self):
        p=payload('deepseek32atlas','judge',{'x':1})
        self.assertEqual(p['provider']['only'],['atlas-cloud/fp8'])
        self.assertEqual(p['provider']['quantizations'],['fp8'])
        self.assertEqual(p['temperature'],0)
        self.assertNotIn('seed',p)
        self.assertNotEqual(fingerprint(p),fingerprint(payload('gpt54flex','judge',{'x':1})))

    def test_http_error_records_status_without_leaking_body_and_does_not_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ledger,credential=self.fixture(root)
            error=urllib.error.HTTPError('https://example.invalid',429,'test',None,io.BytesIO(b'private error body'))
            with patch('budgeted_hosted_frontier_pair.urllib.request.urlopen',side_effect=error) as http:
                with self.assertRaises(urllib.error.HTTPError):
                    request_json('gpt54flex','judge',{'x':1},root/'cache',credential,budget_file=ledger)
                with self.assertRaises(RuntimeError):
                    request_json('gpt54flex','judge',{'x':1},root/'cache',credential,budget_file=ledger)
                self.assertEqual(http.call_count,1)
            diagnostic=next((root/'cache').glob('*-http-error.json')).read_text()
            self.assertEqual(json.loads(diagnostic)['status_code'],429)
            self.assertNotIn('private error body',diagnostic)
            self.assertGreater(json.loads(ledger.read_text())['reserved_microusd'],0)

    def test_dated_model_and_provider_identity_are_checked_after_settlement(self):
        for provider,expected_success in [('OpenAI',True),('Azure',False)]:
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);ledger,credential=self.fixture(root)
                raw={'model':'openai/gpt-5.4-20260305','provider':provider,'id':'mock',
                     'usage':{'cost':.001},'choices':[{'finish_reason':'stop','message':{'content':'{"score": 2}'}}]}
                with patch('budgeted_hosted_frontier_pair.urllib.request.urlopen',return_value=io.StringIO(json.dumps(raw))):
                    if expected_success:
                        self.assertEqual(request_json('gpt54flex','judge',{'x':1},root/'cache',credential,budget_file=ledger)['judgment']['score'],2)
                    else:
                        with self.assertRaisesRegex(ValueError,'provider differs'):
                            request_json('gpt54flex','judge',{'x':1},root/'cache',credential,budget_file=ledger)
                self.assertEqual(json.loads(ledger.read_text())['spent_microusd'],1000)


if __name__=='__main__':unittest.main()
