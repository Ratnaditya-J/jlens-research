import unittest
from metrics import operating_point,paired_cluster_difference,disagreement_table,operating_point_with_cluster_uncertainty


class MetricsTest(unittest.TestCase):
    def test_repeated_seeds_do_not_manufacture_independent_families(self):
        y=[0,1,0,1];scores=[.9,.9,.1,.1];groups=['a','a','b','b']
        base=operating_point_with_cluster_uncertainty(y,scores,groups,.5,replicates=200)
        repeated=operating_point_with_cluster_uncertainty(y*100,scores*100,groups*100,.5,replicates=200)
        self.assertEqual(base['family_cluster_uncertainty'],repeated['family_cluster_uncertainty'])
        self.assertEqual(base['family_cluster_uncertainty']['tpr']['ci95'],[0.,1.])
        self.assertEqual(base['family_cluster_uncertainty']['fpr']['ci95'],[0.,1.])

    def test_unavailable_class_and_single_contributing_family_are_explicit(self):
        report=operating_point_with_cluster_uncertainty([1,0,1,0],[None,.8,None,None],['a','a','b','b'],.5,replicates=200)
        self.assertEqual(report['missingness_tpr_bounds'],[0.,1.])
        self.assertEqual(report['missingness_fpr_bounds'],[.5,1.])
        self.assertEqual(report['family_cluster_uncertainty']['tpr']['valid_replicates'],0)
        self.assertIsNone(report['family_cluster_uncertainty']['tpr']['ci95'])
        self.assertEqual(report['family_cluster_uncertainty']['fpr']['contributing_families'],1)
        self.assertIsNone(report['family_cluster_uncertainty']['fpr']['ci95'])
        empty=operating_point_with_cluster_uncertainty([],[],[],.5,replicates=20)
        self.assertEqual(empty['n'],0)
        self.assertIsNone(empty['family_cluster_uncertainty']['fpr']['ci95'])

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
