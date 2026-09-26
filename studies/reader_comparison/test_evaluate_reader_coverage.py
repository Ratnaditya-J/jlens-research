import unittest
from evaluate_reader_coverage import summarize


class CoverageTests(unittest.TestCase):
    def valid(self):
        return {'status':'ok','judgment':{'score':1,'confidence':'high'}}

    def test_empty_stratum_rejected_despite_high_overall_coverage(self):
        results = {str(i):self.valid() for i in range(20)}
        results['19'] = {'status':'unavailable','error':'Truncated local response'}
        report = summarize(results, {'healthy':[str(i) for i in range(19)],'missing':['19']})
        self.assertEqual(report['usable_fraction'], .95)
        self.assertEqual(report['all_unavailable_strata'], ['missing'])
        self.assertFalse(report['passed'])

    def test_json_without_valid_score_is_unavailable(self):
        report = summarize({'one':{'status':'ok','judgment':{'score':True,'confidence':'high'}}}, {'arm':['one']})
        self.assertEqual(report['usable_requests'], 0)
        self.assertFalse(report['passed'])

    def test_shared_requests_not_double_counted(self):
        report = summarize({'one':self.valid()}, {'arm1':['one'],'arm2':['one']})
        self.assertEqual(report['unique_requests'], 1)
        self.assertTrue(report['passed'])

    def test_missing_request_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            summarize({'one':self.valid()}, {'arm':['one','two']})


if __name__ == '__main__':
    unittest.main()
