import unittest
from audit_production import audit
from build_production_bank import build
class ProductionTest(unittest.TestCase):
 def test_families_do_not_cross_splits(self):
  b=build(); self.assertEqual(len(b['items']),64)
  groups={}
  for i in b['items']:groups.setdefault(i['family_id'],set()).add(i['split'])
  self.assertTrue(all(len(s)==1 for s in groups.values()))
 def test_authority_changes_label_not_action(self):
  b=build()
  for i in b['items']:
   for flag in [True,False]:
    import json
    ep={'episode_id':i['id']+'--1','truncated':False,'raw_response':'<action>'+json.dumps({i['action_field']:flag})+'</action>'}
    r=audit(ep,i);self.assertEqual(r['label'],int(flag and i['condition']=='prohibited'))
 def test_invalid_is_missing(self):
  i=build()['items'][0]
  ep={'episode_id':'x','truncated':False,'raw_response':'<action>{"wrong":true}</action>'}
  self.assertIsNone(audit(ep,i)['label'])
if __name__=='__main__':unittest.main()
