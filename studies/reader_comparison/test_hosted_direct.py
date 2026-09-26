import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from budgeted_hosted_direct import payload, request_json
from hosted_text_reader_direct import run_jobs
from contracts import fingerprint


class DirectReaderTest(unittest.TestCase):
    def test_reasoning_off_preserves_rubric_and_evidence(self):
        evidence={'tokens':['</think>']};p=payload('deepseek32direct','unchanged',evidence)
        self.assertEqual(p['reasoning'],{'enabled':False})
        self.assertEqual(p['messages'][0]['content'],'unchanged')
        self.assertEqual(json.loads(p['messages'][1]['content']),evidence)
        self.assertEqual(p['provider']['only'],['siliconflow/fp8'])
        self.assertFalse(p['provider']['allow_fallbacks'])

    def test_first_http_failure_stops_all_remaining_dispatches(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);jobs=[];keys=[]
            for n in range(6):
                evidence={'text':str(n)};request={'system':'judge','evidence':evidence}
                jobs.append({'request_id':fingerprint(request),**request})
                keys.append(fingerprint(payload('deepseek32direct','judge',evidence)))
            jp=r/'jobs.json';jp.write_text(json.dumps({'jobs':jobs}))
            bp=r/'budget.json';bp.write_text(json.dumps({'status':'active','additional_limit_usd':5,'active_request_allowlist':keys,'records':{}}))
            cp=r/'credential.json';cp.write_text(json.dumps({'OPENROUTER_API_KEY':'test-secret'}))
            error=urllib.error.HTTPError('https://example.invalid',400,'test',None,io.BytesIO(b'test-secret body'))
            with patch('budgeted_hosted_direct.urllib.request.urlopen',side_effect=error) as http:
                run_jobs('deepseek32direct',jp,r/'out',cp,bp)
                self.assertEqual(http.call_count,1)
            ledger=json.loads(bp.read_text());self.assertEqual(ledger['status'],'paused_http_error')
            self.assertEqual(len(ledger['records']),1);self.assertGreater(ledger['reserved_microusd'],0)
            rows=[json.loads(p.read_text()) for p in (r/'out'/'results').glob('*.json')]
            self.assertEqual(len(rows),6);self.assertTrue(all(x['status']=='unavailable' for x in rows))
            self.assertNotIn('test-secret',next((r/'out'/'api-cache').glob('*http-error.json')).read_text())
