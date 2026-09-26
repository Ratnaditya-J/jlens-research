import unittest
from prepare_independent_validation_reviews import independent_jobs
from local_reader_jobs import review_jobs
from test_local_reader_jobs import row

class IndependentValidationTest(unittest.TestCase):
    def test_exact_reuse_with_full_review_payloads_and_no_test(self):
        rows=[row('a','x'),row('b','y')]
        test=row('heldout','z');test['split']='test'
        partial,aliases,donors=independent_jobs({'rows':rows+[test]})
        full,full_aliases,full_donors=review_jobs(rows,{'a':{'20':'summary-a'},'b':{'20':'summary-b'}})
        lookup={j['request_id']:j for j in full}
        self.assertTrue(all(j==lookup[j['request_id']] for j in partial))
        self.assertEqual(donors,full_donors)
        self.assertEqual(aliases,[a for a in full_aliases if not a['arm'].startswith('j_summary')])
        self.assertTrue(all(a['episode_id']!='heldout' for a in aliases))
        self.assertEqual(len(aliases),12)

if __name__=='__main__': unittest.main()
