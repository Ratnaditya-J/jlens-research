import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_timing_positions import sampled_earliest

class Timing(unittest.TestCase):
    def test_earliest_flagged_sample_not_missing(self):
        rows=[{'offset_before_code_onset':o,'flag':f} for o,f in [(0,True),(32,True),(64,None)]]
        r=sampled_earliest(rows,'flag');self.assertEqual(r['earliest_flagged_sample_offset'],32);self.assertEqual(r['missing_offsets'],[64])
    def test_no_flags_is_null_not_zero(self):
        rows=[{'offset_before_code_onset':0,'flag':False},{'offset_before_code_onset':32,'flag':None}]
        self.assertIsNone(sampled_earliest(rows,'flag')['earliest_flagged_sample_offset'])

if __name__=='__main__':unittest.main()
