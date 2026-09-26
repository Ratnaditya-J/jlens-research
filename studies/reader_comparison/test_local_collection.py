import unittest
from collect_local_readers import aggregate, valid_score
from interpret_readers import ARMS


class LocalCollectionTest(unittest.TestCase):
    def test_no_silent_single_reviewer_fallback(self):
        aliases = [{'episode_id': 'a', 'arm': arm, 'request_id': arm} for arm in ARMS]
        good = {'status': 'ok', 'judgment': {'score': 2, 'confidence': 'high'}}
        first = {arm: good for arm in ARMS}
        rows = aggregate(aliases, [first, {}])
        self.assertTrue(all(rows[0][arm]['missing'] for arm in ARMS))
        self.assertTrue(all(rows[0][arm]['score'] is None for arm in ARMS))

    def test_ordinal_minimum_and_individual_scores_retained(self):
        aliases = [{'episode_id': 'a', 'arm': arm, 'request_id': arm} for arm in ARMS]
        first = {arm: {'status': 'ok', 'judgment': {'score': 2, 'confidence': 'high'}} for arm in ARMS}
        second = {arm: {'status': 'ok', 'judgment': {'score': 1, 'confidence': 'medium'}} for arm in ARMS}
        rows = aggregate(aliases, [first, second])
        self.assertEqual(rows[0]['oracle']['score'], 1)
        self.assertEqual(rows[0]['oracle']['reviewer_scores'], [2, 1])

    def test_malformed_valid_json_is_not_a_valid_score(self):
        for judgment in [{'score': True, 'confidence': 'high'}, {'score': 2}, {'score': 3, 'confidence': 'high'}]:
            self.assertIsNone(valid_score({'status': 'ok', 'judgment': judgment}))


if __name__ == '__main__':
    unittest.main()
