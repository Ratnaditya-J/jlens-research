import unittest
from blindspots import probe_display_blindspots

class BlindspotTest(unittest.TestCase):
    def test_missing_oracle_does_not_hide_display_failures(self):
        thresholds={k:1 for k in ['raw_probe','j_tokens_context','j_summary_context','jspace_probe','oracle_context','context_only']}
        row={'episode_id':'a','label':1,'scores':{'raw_probe':2,'j_tokens_context':0,'j_summary_context':0,'jspace_probe':2}}
        out=probe_display_blindspots([row],thresholds)
        self.assertEqual(len(out['probe_detected_jdisplay_missed']),1)
        self.assertIsNone(out['probe_detected_jdisplay_missed'][0]['oracle_detected'])
        self.assertTrue(out['probe_detected_jdisplay_missed'][0]['jspace_probe_detected'])

    def test_summary_failure_is_not_token_failure_and_missing_is_not_negative(self):
        thresholds={k:1 for k in ['raw_probe','j_tokens_context','j_summary_context','jspace_probe','oracle_context','context_only']}
        rows=[{'episode_id':'token-hit','label':1,'scores':{'raw_probe':2,'j_tokens_context':2,'j_summary_context':0}}, {'episode_id':'unavailable','label':1,'scores':{'raw_probe':2,'j_tokens_context':None,'j_summary_context':0}}, {'episode_id':'benign','label':0,'scores':{'raw_probe':2,'j_tokens_context':0,'j_summary_context':0}}]
        out=probe_display_blindspots(rows,thresholds)
        self.assertEqual(len(out['probe_detected_jsummary_missed']),2)
        self.assertEqual(out['probe_detected_jtokens_missed'],[])
        self.assertEqual(out['probe_detected_jdisplay_missed'],[])
        self.assertEqual([r['episode_id'] for r in out['probe_detected_jdisplay_unavailable']],['unavailable'])

if __name__=='__main__':unittest.main()
