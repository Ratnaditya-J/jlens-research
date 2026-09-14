import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from source_parser import extract_code_and_files
class SourceParserTests(unittest.TestCase):
    def test_named_files(self):
        s,files=extract_code_and_files('```python\ndef solution(x): return x\n```\n```python\n# filename: conftest.py\nx=1\n```')
        self.assertEqual(s,'def solution(x): return x');self.assertEqual(files,{'conftest.py':'x=1'})
    def test_xml_solution(self):
        self.assertEqual(extract_code_and_files('<file path="solution.py">a=1</file>')[0],'a=1')
    def test_preserve_invalid_bare_output(self):
        text='<thinking>bad format</thinking>\ndef solution(x): return x'
        self.assertEqual(extract_code_and_files(text)[0],text)
    def test_malformed_channel_with_fence(self):
        self.assertEqual(extract_code_and_files('<|channel|>final <|constrain|>```python\nimport os\nos._exit(0)\n```')[0],'import os\nos._exit(0)')
if __name__=='__main__':unittest.main()
