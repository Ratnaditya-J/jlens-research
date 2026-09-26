import unittest
from individual_readers import calibrate_individuals, evaluate_individuals, individual_score


class IndividualReadersTest(unittest.TestCase):
    def test_independent_thresholds_and_missingness(self):
        calibration_scores = {'benign': {'oracle': {'reviewer_scores': [0, 1]}}}
        calibration = calibrate_individuals(calibration_scores, ['benign'], ['oracle'], ['gptoss', 'qwen'])
        self.assertLess(calibration['gptoss']['oracle']['threshold'], calibration['qwen']['oracle']['threshold'])
        episodes = [{'episode_id': 'positive', 'label': 1}, {'episode_id': 'negative', 'label': 0}]
        test_scores = {'positive': {'oracle': {'reviewer_scores': [1, 1]}},
                       'negative': {'oracle': {'reviewer_scores': [None, 1]}}}
        report = evaluate_individuals(episodes, test_scores, calibration)
        self.assertEqual(report['gptoss']['oracle']['tp'], 1)
        self.assertEqual(report['gptoss']['oracle']['unavailable'], 1)
        self.assertEqual(report['qwen']['oracle']['tp'], 0)
        self.assertEqual(report['qwen']['oracle']['fp'], 0)

    def test_boolean_score_is_not_ordinal(self):
        self.assertIsNone(individual_score({'a': {'reviewer_scores': [True]}}, 'a', 0))


if __name__ == '__main__':
    unittest.main()
