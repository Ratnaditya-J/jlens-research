import unittest
from local_text_reader import final_text
from evaluate_local_bridge import evaluate
class LocalReaderTest(unittest.TestCase):
 def test_reasoning_cannot_be_mistaken_for_final_answer(self):
  with self.assertRaises(ValueError):final_text('<|channel|>analysis<|message|>{"score":2}','gptoss')
  self.assertEqual(final_text('analysis<|channel|>final<|message|>{"score":0}<|return|>','gptoss'),'{"score":0}')
 def test_qwen_terminal_marker_removed(self):
  self.assertEqual(final_text('{"score":1}<|im_end|><|im_end|>','qwen'),'{"score":1}')
 def test_missing_and_boolean_scores_count_as_failures(self):
  refs=[{'request_id':str(i),'reference_score':1} for i in range(3)]
  results={'0':{'manifest_sha256':'m','status':'ok','judgment':{'score':1,'confidence':'high'}},'1':{'manifest_sha256':'m','status':'ok','judgment':{'score':True,'confidence':'high'}}}
  result=evaluate(refs,results,'m')
  self.assertEqual(result['valid_fraction'],1/3)
  self.assertEqual(result['exact_agreement_fraction'],1/3)
 def test_stale_manifest_rejected(self):
  with self.assertRaises(ValueError):evaluate([{'request_id':'x','reference_score':0}],{'x':{'manifest_sha256':'stale'}},'current')
if __name__=='__main__':main()
