import unittest
from metrics import operating_point,paired_cluster_difference,disagreement_table


class MetricsTest(unittest.TestCase):
    def test_identity_comparison_has_zero_paired_difference(self):
        y=[0,1,0,1,0,1,0,1];s=[.1,.9,.2,.8,.3,.7,.4,.6]
        r=paired_cluster_difference(y,s,s,['a','a','b','b','c','c','d','d'],.5,.5,replicates=50)
        self.assertEqual(r['tpr']['ci95'],[0.,0.]);self.assertEqual(r['fpr']['ci95'],[0.,0.])

    def test_probe_only_positive_and_false_alarms_are_separate(self):
        d=disagreement_table([1,0,1],{'probe':[True,True,False],'jlens':[False,False,False],'oracle':[False,True,False]})
        self.assertEqual(d['probe'],{'positive':1,'benign':0})
        self.assertEqual(d['probe + oracle'],{'positive':0,'benign':1})
        self.assertEqual(d['none'],{'positive':1,'benign':0})

    def test_ties_use_frozen_inclusive_rule(self):
        r=operating_point([0,1,0,1],[0,.5,.5,1],.5)
        self.assertEqual((r['tp'],r['fp']),(2,1))


if __name__=='__main__':unittest.main()
