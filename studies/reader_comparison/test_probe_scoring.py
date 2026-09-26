import unittest,numpy as np
from probe_scoring import score_row,score_rows
from contracts import conservative_threshold
class ScoreTest(unittest.TestCase):
 def test_batch_and_single_scores_preserve_conservative_ties(self):
  rng=np.random.default_rng(4);x=rng.normal(size=5120);w=rng.normal(size=5120);batch=np.repeat(x[None,:],8,axis=0);s=score_rows(batch,w,1.3);threshold=conservative_threshold(s)
  self.assertTrue(all(score_row(row,w,1.3)<threshold for row in batch[::-1]));self.assertTrue(np.all(s==s[0]))
 def test_nonfinite_and_wrong_width_rejected(self):
  with self.assertRaises(ValueError):score_row([float('nan')],[1.],0)
  with self.assertRaises(ValueError):score_row([1,2],[1],0)
if __name__=='__main__':unittest.main()
