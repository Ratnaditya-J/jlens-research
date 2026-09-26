import unittest
from metrics import operating_point_with_coverage


class CoverageBoundsTest(unittest.TestCase):
    def test_missing_positive_is_not_a_negative(self):
        result = operating_point_with_coverage([1, 1, 0], [2, None, None], 1)
        self.assertEqual(result['tpr'], 1)
        self.assertEqual(result['missingness_tpr_bounds'], [.5, 1])
        self.assertIsNone(result['fpr'])
        self.assertEqual(result['missingness_fpr_bounds'], [0, 1])
        self.assertEqual(result['unavailable'], 2)

    def test_complete_coverage_bounds_equal_observed_rate(self):
        result = operating_point_with_coverage([1, 0, 0], [2, 2, 0], 1)
        self.assertEqual(result['missingness_tpr_bounds'], [1, 1])
        self.assertEqual(result['missingness_fpr_bounds'], [.5, .5])

    def test_unknown_labels_cannot_be_assumed_benign(self):
        with self.assertRaises(ValueError):
            operating_point_with_coverage([None], [1], 1)


if __name__ == '__main__':
    unittest.main()
