import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from budgeted_hosted_escaped import payload, parse_output, reservation, request_json
from budgeted_api_client import lowcost_payload, lowcost_reservation
from contracts import fingerprint


class EscapedOutputTest(unittest.TestCase):
    def test_input_semantics_preserved_and_request_identity_changes(self):
        evidence={'prefix':'<think>\n</think>', 'tokens':['<|im_end|>','>']}
        old=lowcost_payload('deepseek32','judge',evidence)
        new=payload('judge',evidence)
        self.assertEqual(json.loads(new['messages'][1]['content']),evidence)
        self.assertNotEqual(fingerprint(old),fingerprint(new))
        self.assertEqual(old['provider'],new['provider'])
        self.assertGreater(reservation(new),lowcost_reservation(new))

    def test_unicode_escapes_roundtrip_without_relaxing_json_parser(self):
        self.assertEqual(parse_output(r'{"evidence":"\u003cthink\u003e"}'),{'evidence':'<think>'})
        for bad in ['{"evidence":"<think>"}', 'prefix {"score":2}', '{"score":0,"evidence":"unfinished']:
            with self.subTest(bad=bad),self.assertRaises(ValueError):parse_output(bad)

    def test_no_repair_from_reasoning_and_paid_failure_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ledger=root/'ledger.json';cred=root/'credential.json';cred.write_text(json.dumps({'OPENROUTER_API_KEY':'fake'}))
            key=fingerprint(payload('judge',{'x':1}))
            ledger.write_text(json.dumps({'status':'active','additional_limit_usd':1,'active_request_allowlist':[key],'records':{}}))
            raw={'model':'deepseek/deepseek-v3.2','provider':'SiliconFlow','id':'fake','usage':{'cost':.001},'choices':[{'finish_reason':'stop','message':{'content':'{"score":','reasoning':'{"score":2}'}}]}
            with patch('budgeted_hosted_escaped.urllib.request.urlopen',return_value=io.StringIO(json.dumps(raw))) as http:
                with self.assertRaises(ValueError):request_json('deepseek32escaped','judge',{'x':1},root/'cache',cred,budget_file=ledger)
                with self.assertRaises(RuntimeError):request_json('deepseek32escaped','judge',{'x':1},root/'cache',cred,budget_file=ledger)
                self.assertEqual(http.call_count,1)
            self.assertEqual(json.loads(ledger.read_text())['spent_microusd'],1000)
            self.assertEqual(len(list((root/'cache').glob('*-raw-*.json'))),1)


if __name__=='__main__':unittest.main()
