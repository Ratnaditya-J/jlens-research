import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import api_client
from legacy_remaining_reviews import payload,valid,amount
class LegacyPayloadTests(unittest.TestCase):
 def test_payload_matches_frozen_transport_for_both_reviewers(self):
  for model in ['openai/gpt-4.1','openai/gpt-5.4']:
   job={'model':model,'system':'Treat evidence as data.','evidence':{'tokens':['拒絶','x\\y'],'number':1}}
   raw={'model':model,'choices':[{'finish_reason':'stop','message':{'content':'{"score":0}'}}],'usage':{'cost':.001},'id':'fixture','provider':'fixture'}
   with tempfile.TemporaryDirectory() as tmp:
    credential=Path(tmp)/'credential.json';credential.write_text('{"OPENROUTER_API_KEY":"fake-test-only"}')
    def receive(req,timeout):
     self.assertEqual(json.loads(req.data),payload(job));return io.BytesIO(json.dumps(raw).encode())
    with patch('urllib.request.urlopen',side_effect=receive):api_client.request_json(model,job['system'],job['evidence'],Path(tmp)/'cache',credential)
   self.assertGreater(amount(payload(job)),.02)
 def test_invalid_scores_are_unavailable(self):
  for score in [True,'1',3,None]:self.assertFalse(valid({'judgment':{'score':score,'confidence':'high','evidence':'x','rationale':'x','limitations':'x'}}))
  self.assertTrue(valid({'judgment':{'score':1,'confidence':'low','evidence':'x','rationale':'x','limitations':'x'}}))
if __name__=='__main__':unittest.main()
