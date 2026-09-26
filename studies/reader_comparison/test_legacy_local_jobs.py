import unittest
from legacy_local_jobs import prepare


class LegacyJobsTest(unittest.TestCase):
    def test_summary_does_not_receive_candidate_ranks_or_context(self):
        view = {'episode_id': 'a', 'layers': [{'layer': 7, 'top_tokens': [{'id': 1, 'text': 'word', 'logit': 1.0}],
                                             'candidate_ranks': [{'id': 9, 'text': 'cheat', 'rank': 9, 'logit': 0.5}]}]}
        views = [view, dict(view, episode_id='b')]
        contexts = {eid: {'prompt': 'sensitive context', 'generated_prefix': 'prefix'} for eid in ['a', 'b']}
        jobs, aliases, _ = prepare(views, contexts, {})
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['evidence'], {'TOKEN READOUTS': 'word (1.00)'})
        self.assertEqual(len(aliases), 2)

    def test_local_baselines_and_blind_arms_receive_separate_evidence(self):
        views = [{'episode_id': eid, 'layers': [{'layer': 7, 'top_tokens': [], 'candidate_ranks': []}]} for eid in ['a', 'b']]
        contexts = {eid: {'prompt': 'context-'+eid, 'generated_prefix': 'prefix-'+eid} for eid in ['a', 'b']}
        base = {'rubric': 'rubric', 'jview_score': 'view score', 'context_only_score': 'context score'}
        jobs, aliases, donors = prepare(views, contexts, base, {'a': {'7': 'summary-a'}, 'b': {'7': 'summary-b'}})
        jobs = {j['request_id']: j for j in jobs}
        evidence = {a['arm']: jobs[a['request_id']]['evidence'] for a in aliases if a['episode_id'] == 'a'}
        self.assertEqual(len(evidence), 7)
        self.assertNotIn('task_context', evidence['jsummary_blind'])
        self.assertNotIn('jspace_layers', evidence['context_only'])
        self.assertEqual(evidence['jsummary_shuffled']['task_context'], 'context-a')
        self.assertEqual(evidence['jsummary_shuffled']['layer_interpretations'][0]['interpretation'], 'summary-b')
        self.assertEqual(donors['a'], 'b')


if __name__ == '__main__':
    unittest.main()
