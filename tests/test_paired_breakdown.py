"""Synthetic accounting checks; these fixtures are not experimental results."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('paired', Path(__file__).parents[1]/'scripts/paired_breakdown.py')
paired = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paired)

class AccountingTests(unittest.TestCase):
    def fixture(self):
        return {'protocol': {'split': 'test', 'threshold_source': 'validation', 'observation_boundary': 'start_final', 'probe_threshold': .5, 'jlens_threshold': .5}, 'cases': [
            {'episode_id': str(i), 'task_group': str(i), 'behavior_label': 'misaligned' if i%2 else 'benign', 'probe_score': p, 'jlens_score': j}
            for i, (p, j) in enumerate([(.5, .1), (.1, .5), (.9, .9), (.1, .1), (None, .1), (.9, float('nan'))])]}

    def test_exclusions_ties_and_partition(self):
        summary, rows = paired.summarize(self.fixture())
        self.assertEqual(summary['tables']['all']['counts'], dict.fromkeys(paired.CATEGORIES, 1))
        self.assertEqual(summary['tables']['all']['denominator'], 4)
        self.assertEqual(len(summary['excluded']), 2)
        self.assertIsNone(rows[-1]['probe_flag'])
        self.assertEqual(summary['tables']['benign']['denominator'], 2)

    def test_reject_duplicate_and_unfrozen_protocol(self):
        data = self.fixture()
        data['cases'].append(data['cases'][0])
        with self.assertRaises(ValueError): paired.summarize(data)
        data = self.fixture()
        data['protocol']['threshold_source'] = 'test'
        with self.assertRaises(ValueError): paired.summarize(data)

if __name__ == '__main__': unittest.main()
