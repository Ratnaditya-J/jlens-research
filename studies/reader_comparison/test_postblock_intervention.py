import unittest
try:
    import torch
except ImportError:
    torch=None
from postblock_intervention import PostBlockEdit


@unittest.skipIf(torch is None,'Torch-specific tests run in the separate CPU lens-audit environment')
class PostBlockInterventionTest(unittest.TestCase):
    def test_single_site_and_cached_decode_are_distinct(self):
        block=torch.nn.Identity();x=torch.zeros(1,3,2);edit=PostBlockEdit([3.,4.],5.,prefix_length=3,position=1)
        with edit.attached(block):
            y=block(x);later=torch.zeros(1,1,2);z=block(later)
        self.assertTrue(torch.equal(y[0,1],torch.tensor([3.,4.])))
        self.assertEqual(int(torch.count_nonzero(y)),2);self.assertTrue(torch.equal(x,torch.zeros_like(x)))
        self.assertIs(z,later);self.assertEqual(len(edit.records),1);self.assertAlmostEqual(edit.records[0]['actual_delta_l2'],5.)
        self.assertIs(block(x),x)

    def test_persistent_edits_prefill_site_and_each_decode(self):
        block=torch.nn.Identity();edit=PostBlockEdit([1.,0.],-2.,prefix_length=2,position=1,mode='persistent')
        with edit.attached(block):
            block(torch.zeros(1,2,2));y=block(torch.zeros(1,1,2));block(torch.zeros(1,1,2))
        self.assertEqual(len(edit.records),3);self.assertEqual(y[0,0,0].item(),-2.)
        self.assertEqual([r['phase'] for r in edit.records],['prefill','decode','decode'])

    def test_zero_dose_is_exact_tuple_identity(self):
        x=torch.randn(1,2,2);tail=object();out=(x,tail);edit=PostBlockEdit([1.,2.],0.,prefix_length=2,position=0)
        self.assertIs(edit(None,None,out),out);self.assertEqual(edit.records[0]['actual_delta_l2'],0.)

    def test_bad_cache_shape_fails_and_hook_is_removed(self):
        block=torch.nn.Identity();edit=PostBlockEdit([1.,0.],1.,prefix_length=2,position=0)
        with self.assertRaisesRegex(ValueError,'Fresh full-prefix'):
            with edit.attached(block):block(torch.zeros(1,1,2))
        self.assertFalse(block._forward_hooks)
        with self.assertRaisesRegex(ValueError,'fresh edit'):
            with edit.attached(block):pass

    def test_no_cache_replay_and_unvisited_site_are_rejected(self):
        block=torch.nn.Identity();edit=PostBlockEdit([1.,0.],1.,prefix_length=2,position=0)
        with self.assertRaisesRegex(ValueError,'Cached single-token'):
            with edit.attached(block):block(torch.zeros(1,2,2));block(torch.zeros(1,3,2))
        with self.assertRaisesRegex(ValueError,'never visited'):
            with PostBlockEdit([1.,0.],1.,prefix_length=2,position=0).attached(block):pass
