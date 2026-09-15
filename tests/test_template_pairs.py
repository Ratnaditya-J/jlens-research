import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_template_pairs import pair_cases
class Pairs(unittest.TestCase):
 def test_changed_behavior_is_not_automatically_a_miss(self):
  primary=[{'episode_id':'p','task_group':'f','behavior_label':'misaligned','category':'both','probe_flag':True,'jlens_flag':True}]
  challenge=[{'episode_id':'c','matched_primary_episode_id':'p','task_group':'f','template':'new','behavior_label':'benign','category':'neither','probe_flag':False,'jlens_flag':False}]
  pairs,excluded,transitions=pair_cases(primary,challenge)
  self.assertEqual(pairs[0]['effects']['probe_accuracy_difference'],0)
  self.assertNotIn('probe_sensitivity_difference_stable_positive',pairs[0]['effects'])
  self.assertEqual(transitions,{'misaligned -> benign':1});self.assertEqual(excluded,[])
  challenge[0]['behavior_label']='uncertain'
  self.assertEqual(pair_cases(primary,challenge)[1],['c'])
  challenge[0]['task_group']='different'
  with self.assertRaises(AssertionError):pair_cases(primary,challenge)
if __name__=='__main__':unittest.main()
