import tempfile,unittest
from pathlib import Path
from contracts import fingerprint
from smoke import write_json
from test_accepted_review_receipts import ReceiptIntegrityTests
from finish_primary_with_missing import verify_result


class MissingReceiptTests(unittest.TestCase):
 def test_truncation_is_accounted_for_without_inventing_score(self):
  job,result,raw,record=ReceiptIntegrityTests().fixture()
  result={'request_id':result['request_id'],'manifest_sha256':result['manifest_sha256'],'status':'unavailable','error_type':'ValueError'}
  raw['response']['choices'][0]['finish_reason']='length'
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'api-cache').mkdir();path=root/'api-cache'/(fingerprint(raw['request'])+'-raw-1.json');write_json(path,raw)
   verify_result(job,result,[root],'gpt41reference','reference',{'records':{'token':record}})
   self.assertNotIn('judgment',result)
   record['actual_microusd']=0
   with self.assertRaises(ValueError):verify_result(job,result,[root],'gpt41reference','reference',{'records':{'token':record}})
 def test_other_failures_are_not_automatically_accepted(self):
  job,result,raw,record=ReceiptIntegrityTests().fixture();result.update(status='unavailable',error_type='ValueError')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'api-cache').mkdir();write_json(root/'api-cache'/(fingerprint(raw['request'])+'-raw-1.json'),raw)
   with self.assertRaises(ValueError):verify_result(job,result,[root],'gpt41reference','reference',{'records':{'token':record}})
