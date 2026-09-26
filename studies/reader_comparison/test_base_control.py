import unittest
from compare_base_behavior import compare
class BaseControlTest(unittest.TestCase):
 def test_violation_and_authorized_utility_are_distinct(self):
  base=[];subject={}
  for family in ['one','two']:
   for condition in ['prohibited','authorized']:
    eid=family+condition;b={'episode_id':eid,'split':'train','family_id':family,'condition':condition,'status':'ok','label':int(condition=='prohibited'),'state':{'named_action_executed':condition=='prohibited'}};s=dict(b,label=0,state={'named_action_executed':condition=='authorized'});base.append(b);subject[eid]=s
  result=compare(base,subject)
  self.assertEqual(result['prohibited']['subject_minus_base_rate'],-1)
  self.assertEqual(result['authorized']['subject_minus_base_rate'],1)
  self.assertEqual(result['prohibited']['family_bootstrap_95ci'],[-1,-1])
 def test_heldout_rows_are_rejected(self):
  with self.assertRaises(ValueError):compare([{'split':'test'}],{})
if __name__=='__main__':unittest.main()
