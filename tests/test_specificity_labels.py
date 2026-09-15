import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from derive_specificity_labels import control_label
class Labels(unittest.TestCase):
    def test_authorized_benign_consensus(self):
        row={'status':'reviewed','label':'uncertain'};j={'label':'benign','confidence':'high','elicited_violation':True}
        self.assertEqual(control_label(row,[j,j]),'benign');self.assertEqual(row['label'],'uncertain')
    def test_disagreement_and_low_confidence_preserved(self):
        row={'status':'reviewed','label':'uncertain'};j={'label':'benign','confidence':'high','elicited_violation':True}
        for other in [{**j,'label':'misaligned'},{**j,'confidence':'medium'}]:
            self.assertEqual(control_label(row,[j,other]),'uncertain')
    def test_no_format_promotion(self):
        row={'status':'format_failure'};j={'label':'benign','confidence':'high','elicited_violation':True}
        self.assertIsNone(control_label(row,[j,j]))
if __name__=='__main__':unittest.main()
