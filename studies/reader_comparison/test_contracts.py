import copy
import math
import unittest
from contracts import (fingerprint, validate_cell, check_splits, validate_cached_result,
                       paired_rows, conservative_threshold, strictly_before,parse_json_reply)


class ContractsTest(unittest.TestCase):
    def test_json_wrapping_does_not_accept_extraneous_prose(self):
        self.assertEqual(parse_json_reply('```json\n{"ok":true}\n```'),{'ok':True})
        with self.assertRaises(ValueError):parse_json_reply('Ignore rules. {"ok":true}')
        with self.assertRaises(ValueError):parse_json_reply('[]')

    def test_checkpoint_and_adapter_must_match(self):
        identity={'base':'revision-a','adapter':'revision-b','precision':'bf16'}
        cell={'episode_id':'e','family_id':'f','split':'test','identity_sha256':fingerprint(identity),'prefix_ids':[1,2], 'position':1,'layer':20,'state_sha256':'abc'}
        validate_cell(cell,identity,[20])
        with self.assertRaises(ValueError): validate_cell(cell,{**identity,'adapter':'disabled'},[20])
        with self.assertRaises(ValueError): validate_cell(cell,identity,[24])
        cell['prefix_ids'].append(3)
        with self.assertRaises(ValueError): validate_cell(cell,identity,[20])

    def test_template_siblings_cannot_cross_splits(self):
        rows=[{'episode_id':'1','family_id':'f','split':'train'}, {'episode_id':'2','family_id':'f','split':'test'}]
        with self.assertRaises(ValueError): check_splits(rows)

    def test_partial_and_failed_results_remain_visible(self):
        common,coverage=paired_rows(['a','b','c'],{'probe':[{'cell_id':x,'status':'ok'} for x in 'abc'],'oracle':[{'cell_id':'a','status':'ok'},{'cell_id':'b','status':'refusal'}]})
        self.assertEqual(common,['a'])
        self.assertEqual(coverage['oracle'],{'requested':3,'ok':1,'missing':1})

    def test_caches_bind_entire_request_and_individual_model(self):
        request={'model':'reviewer-a','prompt':'v1','state':'abc','sampling':{'temperature':0}}
        result={'requested_model':'reviewer-a','request_sha256':fingerprint(request),'status':'ok'}
        validate_cached_result(result,request)
        changed=copy.deepcopy(request); changed['sampling']['temperature']=1
        with self.assertRaises(ValueError):validate_cached_result(result,changed)
        with self.assertRaises(ValueError):validate_cached_result({**result,'requested_model':'reviewer-b'},request)

    def test_tied_threshold_does_not_round_to_zero(self):
        threshold=conservative_threshold([0]*100)
        self.assertGreater(threshold,0)
        self.assertEqual(sum(s>=threshold for s in [0]*100),0)
        self.assertEqual(conservative_threshold([1]*20),math.nextafter(1,math.inf))

    def test_straddling_action_token_is_excluded(self):
        self.assertEqual(strictly_before([(0,3),(3,7),(7,10)],6),0)


if __name__=='__main__': unittest.main()
