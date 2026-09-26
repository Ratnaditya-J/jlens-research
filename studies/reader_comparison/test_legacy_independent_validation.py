import unittest
from prepare_legacy_independent_validation import independent_jobs
from legacy_local_jobs import prepare

class LegacyIndependentTest(unittest.TestCase):
    def test_exact_request_reuse_without_summary_evidence(self):
        views=[{'episode_id':e,'layers':[{'layer':7,'top_tokens':[],'candidate_ranks':[]}]} for e in ['a','b']]
        contexts={e:{'prompt':'context-'+e,'generated_prefix':'prefix'} for e in ['a','b']}
        base={'rubric':'rubric','jview_score':'view','context_only_score':'context'}
        partial,aliases,donors=independent_jobs(views,contexts,base)
        full,full_aliases,full_donors=prepare(views,contexts,base,{'a':{'7':'summary-a'},'b':{'7':'summary-b'}})
        lookup={j['request_id']:j for j in full}
        self.assertTrue(all(j==lookup[j['request_id']] for j in partial))
        self.assertEqual(aliases,[a for a in full_aliases if not a['arm'].startswith('jsummary')])
        self.assertEqual(donors,full_donors)
        self.assertTrue(all('layer_interpretations' not in j['evidence'] for j in partial))
        self.assertEqual(len(aliases),6)

if __name__=='__main__':unittest.main()
