import unittest
import json
import copy
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

    def test_json_key_order_cannot_swap_reviewers(self):
        calibration = calibrate_individuals(
            {'benign': {'oracle': {'reviewer_scores': [0, 1]}}},
            ['benign'], ['oracle'], ['gptoss', 'deepseek'])
        reordered = json.loads(json.dumps(calibration, sort_keys=True))
        self.assertEqual(list(reordered), ['deepseek', 'gptoss'])
        episodes = [{'episode_id': 'positive', 'label': 1}]
        scores = {'positive': {'oracle': {'reviewer_scores': [1, 0]}}}
        original = evaluate_individuals(episodes, scores, calibration)
        self.assertEqual(evaluate_individuals(episodes, scores, reordered), original)
        self.assertEqual(original['gptoss']['oracle']['tp'], 1)
        self.assertEqual(original['deepseek']['oracle']['tp'], 0)

    def test_missing_or_duplicate_indices_fail_closed(self):
        calibration = calibrate_individuals(
            {'benign': {'oracle': {'reviewer_scores': [0, 1]}}},
            ['benign'], ['oracle'], ['gptoss', 'deepseek'])
        for replacement in [None, 0, True, -1]:
            altered = copy.deepcopy(calibration)
            altered['deepseek']['oracle']['reviewer_index'] = replacement
            with self.assertRaises(ValueError):
                evaluate_individuals([], {}, altered)


if __name__ == '__main__':
    unittest.main()
