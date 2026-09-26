import unittest
import numpy as np
from lens_activation_stability import summary


class ActivationStabilityTest(unittest.TestCase):
    def test_cosine_agreement_does_not_hide_scale_change(self):
        ref=np.array([[1.,0.],[0.,2.]])
        result=summary(2*ref,ref)
        self.assertEqual(result['cosine_quantiles']['median'],1.)
        self.assertEqual(result['aggregate_relative_error'],1.)
        self.assertEqual(result['relative_error_quantiles']['median'],1.)

    def test_orthogonal_vectors_and_degenerate_inputs(self):
        result=summary(np.array([[1.,0.]]),np.array([[0.,1.]]))
        self.assertEqual(result['cosine_quantiles']['median'],0.)
        self.assertAlmostEqual(result['aggregate_relative_error'],2**.5)
        for value in [0.,np.nan,np.inf]:
            with self.assertRaises(ValueError):summary(np.array([[value,0.]]),np.array([[1.,0.]]))
