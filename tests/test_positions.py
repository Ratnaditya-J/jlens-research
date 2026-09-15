import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.positions import position_manifest,source_line_positions

def fixture(chunks):
    return {'episode_id':'e','identity_sha256':'i','activation_sha256':'a','initial_tokens':10,
      'generated_token_ids':list(range(len(chunks))),'generated_text':''.join(chunks)},lambda ids:''.join(chunks[i] for i in ids)
class Positions(unittest.TestCase):
    def test_source_lines_straddles_and_blanks(self):
        e,d=fixture(['```python\nclass A:\n\n def f(self):\n  ret','urn True\n```'])
        m=source_line_positions(e,d)
        self.assertEqual([r['source_line'] for r in m['lines']],[1,3,4])
        self.assertTrue(all(r['before_statement_sample_index']==0 for r in m['lines']))
        self.assertEqual(e['generated_text'][m['lines'][-1]['character_offset']:][:6],'return')
    def test_source_map_does_not_read_labels(self):
        e,d=fixture(['```python\n','x=1\n```']);a=source_line_positions(e,d)
        e.update(label='misaligned',probe_score=1)
        self.assertEqual(a,source_line_positions(e,d))
    def test_exact_boundary_and_no_future(self):
        e,d=fixture(['reason\n','```python\n','def solution(x):\n',' return x\n','```'])
        m=position_manifest(e,d);self.assertEqual(m['primary_sample_index'],2)
        self.assertEqual(m['permitted_generated_prefix_ids'],[0,1]);self.assertEqual(m['positions']['0']['absolute_residual_token_index'],11)
        self.assertFalse(m['positions']['32']['available'])
    def test_straddled_token_uses_earlier_state(self):
        e,d=fixture(['reason','\n```python\ndef',' solution(x): return x\n```'])
        m=position_manifest(e,d);self.assertEqual(m['primary_sample_index'],1);self.assertTrue(m['boundary_straddled'])
    def test_duplicate_source_is_unavailable(self):
        e,d=fixture(['```python\nx=1\n```\n```python\nx=1\n```'])
        self.assertIn('not unique',position_manifest(e,d)['unavailable'])
    def test_reasoning_code_is_not_submission(self):
        e,d=fixture(['```python\nx=0\n```', '<|channel|>final<|message|>```python\n','x=1\n```'])
        m=position_manifest(e,d);self.assertEqual(m['primary_sample_index'],2)
    def test_changed_decode_rejected(self):
        e,d=fixture(['```python\nx=1\n```']);e['generated_text']='changed'
        self.assertIn('differs',position_manifest(e,d)['unavailable'])
    def test_no_label_influence(self):
        e,d=fixture(['```python\n','x=1\n```']);a=position_manifest(e,d)
        e.update(label='misaligned',probe_score=1,jlens_score=0)
        self.assertEqual(a,position_manifest(e,d))
if __name__=='__main__':unittest.main()
