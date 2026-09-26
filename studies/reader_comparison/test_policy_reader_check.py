import unittest
from build_policy_reader_check import fixtures
from evaluate_local_bridge import evaluate
from contracts import fingerprint


class PolicyReaderCheckTest(unittest.TestCase):
    def test_blind_jobs_and_balanced_fixture_types(self):
        jobs, references = fixtures()
        self.assertEqual(len(jobs), 24)
        self.assertEqual(len({j['request_id'] for j in jobs}), 24)
        self.assertEqual(sum(r['reference_score'] == 2 for r in references), 6)
        for j in jobs:
            self.assertEqual(set(j), {'request_id', 'system', 'evidence'})
            self.assertEqual(j['request_id'], fingerprint({'system': j['system'], 'evidence': j['evidence']}))
        for kind in ['violation', 'authorized', 'refusal', 'quotation']:
            self.assertEqual(sum(r['fixture_type'] == kind for r in references), 6)

    def test_always_benign_cannot_pass_accuracy_gate(self):
        jobs, references = fixtures()
        results = {j['request_id']: {'manifest_sha256': 'm', 'status': 'ok',
                                    'judgment': {'score': 0, 'confidence': 'high'}} for j in jobs}
        report = evaluate(references, results, 'm')
        self.assertEqual(report['exact_agreement_fraction'], .75)


if __name__ == '__main__':
    unittest.main()
