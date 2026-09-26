import unittest
from local_text_reader_reasoning import final_text


class ReasoningReaderTests(unittest.TestCase):
    def test_only_final_response_is_parsed(self):
        raw = 'A speculative {"score": 2} in reasoning. </think>\n{"score": 0, "confidence": "high"}<|im_end|>'
        self.assertEqual(final_text(raw, 'qwen'), '{"score": 0, "confidence": "high"}')

    def test_unfinished_reasoning_is_unavailable(self):
        with self.assertRaisesRegex(ValueError, 'No end of reasoning'):
            final_text('Reasoning contains {"score": 2}', 'qwen')


if __name__ == '__main__':
    unittest.main()
