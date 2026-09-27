import copy
import unittest
from collect_standard_readers import validate_summary_reader, execution_source, aggregate
from hosted_text_reader_standardreference import execution_manifest as standard
from hosted_text_reader_lowreference import execution_manifest as flex

class StandardProtocolTests(unittest.TestCase):
    def test_explicit_summary_and_judge_executions(self):
        validate_summary_reader(flex('gpt54lowreference'), standard('gpt54standardreference'))
        self.assertEqual(execution_source(standard('gpt54standardreference')).name,'hosted_text_reader_standardreference.py')
    def test_rejects_route_or_settings_substitution(self):
        original=standard('gpt54standardreference')
        for field,value in [('endpoint','openai/flex'),('completion_price',7.5)]:
            changed=copy.deepcopy(original);changed['model'][field]=value
            with self.assertRaises(ValueError): execution_source(changed)
            with self.assertRaises(ValueError): validate_summary_reader(flex('gpt54lowreference'),changed)
        with self.assertRaises(ValueError): validate_summary_reader(original,original)
        with self.assertRaises(ValueError): validate_summary_reader(flex('gpt54lowreference'),flex('gpt54lowreference'))
    def test_summary_reasoning_change_rejected(self):
        changed=flex('gpt54lowreference');changed['reasoning_effort']='medium'
        with self.assertRaises(ValueError):validate_summary_reader(changed,standard('gpt54standardreference'))
