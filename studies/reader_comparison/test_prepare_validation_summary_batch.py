import json
import tempfile
import unittest
from pathlib import Path
from prepare_validation_summary_batch import prepare
from contracts import fingerprint
from smoke import digest, write_json


class SummaryBatchTests(unittest.TestCase):
    def fixture(self, root, name, phase='validation'):
        directory = root/name
        directory.mkdir()
        request = {'system':'fixed instruction', 'evidence':{'tokens':['a','b']}}
        job = {**request, 'request_id':fingerprint(request)}
        write_json(directory/'jobs.json', {'jobs':[job]})
        write_json(directory/'aliases.json', [{'request_id':job['request_id']}])
        write_json(directory/'manifest.json', {'phase':phase, 'stage':'summaries',
            'jobs_sha256':digest(directory/'jobs.json'),
            'aliases_sha256':digest(directory/'aliases.json')})
        return directory, job

    def test_exact_duplicate_reused_and_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, job = self.fixture(root, 'one')
            second, _ = self.fixture(root, 'two')
            out = root/'out'
            self.assertEqual(prepare([first,second], out), 1)
            self.assertEqual(json.loads((out/'jobs.json').read_text())['jobs'], [job])
            manifest = json.loads((out/'manifest.json').read_text())
            self.assertEqual(len(manifest['source_hashes']), 6)
            self.assertEqual(manifest['jobs_sha256'], digest(out/'jobs.json'))

    def test_test_partition_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, _ = self.fixture(root, 'test', phase='test')
            with self.assertRaisesRegex(ValueError, 'Only validation'):
                prepare([source], root/'out')
            self.assertFalse((root/'out').exists())

    def test_tampered_payload_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, job = self.fixture(root, 'one')
            job['evidence'] = {'tokens':['changed']}
            write_json(source/'jobs.json', {'jobs':[job]})
            with self.assertRaisesRegex(ValueError, 'Prepared reader input changed'):
                prepare([source], root/'out')
            self.assertFalse((root/'out').exists())


if __name__ == '__main__':
    unittest.main()
