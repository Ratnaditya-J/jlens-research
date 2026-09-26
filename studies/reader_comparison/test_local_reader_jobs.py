import copy
import unittest
from local_reader_jobs import validate_rows, summary_jobs, review_jobs


def row(eid, prefix):
    return {'episode_id': eid, 'family_id': eid, 'split': 'validation',
            'prefix_sha256': prefix, 'prefix_text': 'context-' + prefix,
            'j_tokens': [{'layer': 20, 'tokens': [prefix], 'scores': [1.0], 'token_ids': [1]}],
            'oracle': [{'layer': 20, 'status': 'ok', 'text': 'oracle-' + prefix, 'truncated': False}]}


class LocalReaderJobsTest(unittest.TestCase):
    def test_aliases_deduplicate_identical_displays(self):
        jobs, aliases = summary_jobs([row('a', 'x'), row('b', 'x')])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(len(aliases), 2)
        self.assertNotIn('episode_id', jobs[0])

    def test_context_isolation_and_shuffled_donor(self):
        rows = [row('a', 'x'), row('b', 'y')]
        jobs, aliases, donors = review_jobs(rows, {'a': {'20': 'summary-x'}, 'b': {'20': 'summary-y'}})
        jobs = {j['request_id']: j for j in jobs}
        requests = {a['arm']: jobs[a['request_id']]['evidence'] for a in aliases if a['episode_id'] == 'a'}
        self.assertEqual(len(requests), 9)
        self.assertNotIn('causal_prefix', requests['oracle'])
        self.assertEqual(set(requests['context_only']), {'causal_prefix'})
        self.assertEqual(requests['oracle_shuffled_context']['causal_prefix'], 'context-x')
        self.assertEqual(requests['oracle_shuffled_context']['layers'][0]['description'], 'oracle-y')
        self.assertEqual(donors['x'], 'b')

    def test_missing_summaries_remain_missing(self):
        _, aliases, _ = review_jobs([row('a', 'x'), row('b', 'y')], {})
        self.assertEqual(sum(a['request_id'] is None for a in aliases), 6)

    def test_nested_outcome_leakage_rejected(self):
        original = row('a', 'x')
        for location in ['top', 'tokens', 'oracle']:
            value = copy.deepcopy(original)
            target = value if location == 'top' else value['j_tokens' if location == 'tokens' else 'oracle'][0]
            target['label'] = 1
            with self.assertRaises(ValueError):
                validate_rows({'rows': [value]}, 'validation')


if __name__ == '__main__':
    unittest.main()
