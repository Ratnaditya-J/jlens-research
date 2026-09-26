import unittest
from merge_shards import validate_manifests
class MergeTest(unittest.TestCase):
 def base(self):return {k:'same' for k in ['identity','source_layers','target_layer','skip_first','max_seq_len','dim_batch','corpus_sha256','shuffle_seed','reference_revision']}
 def test_exact_disjoint_plan(self):
  a=dict(self.base(),prompts=['a','b']);b=dict(self.base(),prompts=['c','d']);self.assertEqual(validate_manifests([a,b],['a','b','c','d']),['a','b','c','d'])
 def test_overlap_and_checkpoint_change_fail(self):
  a=dict(self.base(),prompts=['a']);b=dict(self.base(),prompts=['a'])
  with self.assertRaises(ValueError):validate_manifests([a,b],['a','b'])
  b.update(prompts=['b'],identity='other')
  with self.assertRaises(ValueError):validate_manifests([a,b],['a','b'])
if __name__=='__main__':unittest.main()
