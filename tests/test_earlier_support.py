import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from score_earlier_positions import support

class Support(unittest.TestCase):
    def test_requires_classes_in_grouped_folds(self):
        train=[{'feature_index':i,'family_id':str(i),'label':'misaligned' if i==0 else 'benign'} for i in range(4)]
        valid=[{'feature_index':i,'family_id':'val','label':x} for i,x in enumerate(['benign','misaligned'])]
        ok,counts,reason=support({'train':train,'validation':valid})
        self.assertFalse(ok);self.assertIn('fold',reason)
    def test_missing_features_do_not_count(self):
        rows=[{'feature_index':None,'label':x,'family_id':'f'} for x in ['benign','misaligned']]
        ok,counts,reason=support({'train':rows,'validation':rows})
        self.assertFalse(ok);self.assertEqual(counts['train']['misaligned'],0)
    def test_balanced_families(self):
        rows=[{'feature_index':2*f+i,'label':x,'family_id':str(f)} for f in range(4) for i,x in enumerate(['benign','misaligned'])]
        self.assertTrue(support({'train':rows,'validation':rows})[0])

if __name__=='__main__':unittest.main()
