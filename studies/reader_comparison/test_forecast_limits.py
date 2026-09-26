import unittest
from forecast_limits import empirical_limits
class ForecastTest(unittest.TestCase):
 def test_conflicting_identical_prefixes(self):
  r=empirical_limits([{'prefix_sha256':'a','label':x} for x in [0,0,1,1]])
  self.assertEqual(r['optimistic_empirical_accuracy_ceiling'],.5);self.assertEqual(r['optimistic_empirical_tpr_ceiling'],0)
 def test_zero_cost_positive_groups_count_once(self):
  rows=[{'prefix_sha256':'a','label':1},{'prefix_sha256':'b','label':0}];r=empirical_limits(rows)
  self.assertEqual(r['optimistic_empirical_tpr_ceiling'],1)
 def test_whole_groups_not_fractional_predictions(self):
  rows=[{'prefix_sha256':'mixed','label':x} for x in [0,0,1,1,1]]+[{'prefix_sha256':str(i),'label':0} for i in range(18)]
  self.assertEqual(empirical_limits(rows)['optimistic_empirical_tpr_ceiling'],0)
if __name__=='__main__':unittest.main()
