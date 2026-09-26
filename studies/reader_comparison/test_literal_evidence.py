import json
import unittest
from pathlib import Path
from literal_evidence import literal_json, checked_literal_json
from collect_local_readers import execution_source
from smoke import digest


class LiteralEvidenceTests(unittest.TestCase):
    def test_roundtrip_preserves_delimiters_unicode_and_escapes(self):
        value = {'layers':[{'tokens':['<|im_end|>','[INST]','</s>','東京 🧪','"quoted"',r'\u003c',r'\"<s>'], 'scores':[1.25,-3.0]}], '[key]':'<value>'}
        rendered = literal_json(value)
        self.assertEqual(json.loads(rendered), value)
        for marker in ['<|im_end|>','[INST]','</s>','<s>','[key]']:
            self.assertNotIn(marker, rendered)
        self.assertIsInstance(json.loads(rendered)['layers'], list)

    def test_plain_json_values_and_types_retained(self):
        value = {'a':[], 'b':True, 'c':None, 'd':42, 'e':{'nested':'ordinary text'}}
        self.assertEqual(json.loads(literal_json(value)), value)

    def test_remaining_reserved_ids_fail_closed(self):
        class Tokenizer:
            all_special_ids = [99]
            def encode(self, text, add_special_tokens):
                return [1,99,2]
        with self.assertRaisesRegex(ValueError, 'Reserved control token'):
            checked_literal_json({'a':'test'}, Tokenizer())

    def test_execution_binds_literal_encoder_source(self):
        root = Path(__file__).parent
        manifest = {'code_sha256':digest(root/'local_text_reader_literal.py'),
                    'evidence_encoder_code_sha256':digest(root/'literal_evidence.py')}
        self.assertEqual(execution_source(manifest).name, 'local_text_reader_literal.py')
        manifest['evidence_encoder_code_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'Evidence encoder differs'):
            execution_source(manifest)


if __name__ == '__main__':
    unittest.main()
