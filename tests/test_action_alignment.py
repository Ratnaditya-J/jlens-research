import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.action_alignment import align_actions

class Alignment(unittest.TestCase):
    def fixture(self):
        chunks = ['```python\n', 'class A:\n', ' def __eq__(self, x):\n  ret', 'urn True\n```']
        return ({'episode_id':'e', 'generated_token_ids':list(range(4)),
                 'generated_text': ''.join(chunks)},
                {'observables_match_original_audit':True, 'candidate_executed_source_lines':[3]},
                lambda ids: ''.join(chunks[i] for i in ids))
    def test_straddled_statement(self):
        e,t,d = self.fixture(); r = align_actions(e,t,d)
        self.assertEqual(r['actions'][0]['before_statement_sample_index'],2)
        self.assertTrue(r['actions'][0]['token_straddles_statement_boundary'])
        self.assertEqual(e['generated_text'][r['actions'][0]['character_offset']:][:6], 'return')
    def test_invalid_trace_cannot_localize(self):
        e,t,d = self.fixture();t['observables_match_original_audit']=False
        self.assertIn('unavailable',align_actions(e,t,d))
    def test_invalid_line(self):
        e,t,d = self.fixture();t['candidate_executed_source_lines']=[20]
        self.assertIn('unavailable',align_actions(e,t,d))
    def test_no_action_is_not_an_early_detection(self):
        e,t,d = self.fixture();t['candidate_executed_source_lines']=[]
        self.assertEqual(align_actions(e,t,d)['actions'],[])

if __name__ == '__main__': unittest.main()
