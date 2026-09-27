import copy
import json
import unittest
from contracts import fingerprint
from hosted_text_reader_lowreference import execution_manifest
from budgeted_hosted_lowreference import payload
from verify_accepted_summary_receipts import verify_one


class SummaryReceiptIntegrityTests(unittest.TestCase):
    def fixture(self):
        j={'system':'Score the evidence','evidence':{'text':'example'}};j['request_id']=fingerprint(j)
        p=payload('gpt54lowreference',j['system'],j['evidence']);k=fingerprint(p)
        judgment={'interpretation':'A topic-oriented summary.'}
        response={'id':'receipt','model':'openai/gpt-5.4','provider':'OpenAI','usage':{'cost':.002},'choices':[{'finish_reason':'stop','message':{'content':json.dumps(judgment)}}]}
        result={'status':'ok','request_id':j['request_id'],'manifest_sha256':fingerprint(execution_manifest('gpt54lowreference')),'api_request_sha256':k,'raw_response':response,'judgment':judgment}
        raw={'request':p,'response':response,'budget_reservation':'token'}
        record={'request_sha256':k,'status':'settled','response_id':'receipt','actual_microusd':2000}
        return j,result,raw,record
    def test_valid_receipt(self):
        self.assertEqual(verify_one(*self.fixture(),'gpt54lowreference','lowreference'),2000)
    def test_changed_judgment_payload_or_receipt_rejected(self):
        for change in ['judgment','payload','cost','unsettled','response_id']:
            with self.subTest(change=change):
                j,result,raw,record=copy.deepcopy(self.fixture())
                if change=='judgment':result['judgment']={'score':2,'confidence':'high'}
                elif change=='payload':raw['request']['max_tokens']=3200
                elif change=='cost':record['actual_microusd']=0
                elif change=='unsettled':record['status']='reserved'
                else:record['response_id']='other'
                with self.assertRaises(ValueError):verify_one(j,result,raw,record,'gpt54lowreference','lowreference')

    def test_empty_or_extra_field_summary_rejected(self):
        for judgment in [{'interpretation':' '},{'interpretation':'text','score':2}]:
            j,result,raw,record=copy.deepcopy(self.fixture())
            result['judgment']=judgment
            raw['response']['choices'][0]['message']['content']=json.dumps(judgment)
            with self.assertRaises(ValueError):verify_one(j,result,raw,record,'gpt54lowreference','lowreference')
