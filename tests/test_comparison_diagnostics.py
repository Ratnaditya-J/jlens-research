import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.comparison_diagnostics import additional_diagnostics

class Diagnostics(unittest.TestCase):
    def test_ambiguity_uncertainty_and_missingness_are_distinct(self):
        rows = [
            {'behavior_label':'misaligned','probe_score':.9,'jlens_score':1,'category':'probe_only'},
            {'behavior_label':'benign','probe_score':.1,'jlens_score':0,'category':'neither'},
            {'behavior_label':'uncertain','probe_score':.9,'jlens_score':2,'category':'both'},
            {'behavior_label':'misaligned','probe_score':None,'jlens_score':None,'category':None}]
        judgments = [{'jview':{'reviewer_scores':[1,2]},'context_only':{'reviewer_scores':[2,2]}}]
        result = additional_diagnostics(rows, judgments, .5, 2)
        self.assertEqual(result['ordinal_jview_by_label']['misaligned']['ambiguous'],1)
        self.assertEqual(result['ambiguous_excluded_secondary']['n'],1)
        self.assertEqual(result['uncertain_label_sensitivity']['misaligned']['probe']['tp'],2)
        self.assertEqual(result['uncertain_label_sensitivity']['benign']['probe']['fp'],1)
        self.assertEqual(result['reviewer_agreement']['jview']['disagreements'],1)
        self.assertEqual(result['ordinal_test_operating_points']['2']['fn'],1)
        self.assertEqual(result['ordinal_test_operating_points']['2']['excluded'],2)

if __name__ == '__main__': unittest.main()
