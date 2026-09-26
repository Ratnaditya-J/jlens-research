import tempfile
import unittest
from pathlib import Path
from contracts import fingerprint
from smoke import digest, write_json
from prepare_legacy_validation import check_gate


class GateTests(unittest.TestCase):
    def test_failed_or_changed_gate_cannot_release_reviews(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reader, gates = root/'reader', root/'gates'
            reader.mkdir(); gates.mkdir()
            manifest = {'model': 'fixture'}
            write_json(reader/'manifest.json', manifest)
            self.assertFalse(check_gate(gates, reader))
            for name in ['bridge', 'policy']:
                write_json(gates/(name+'.json'), {'passed': True, 'manifest_sha256': fingerprint(manifest)})
            complete = {'passed': True, 'reader_manifest_sha256': digest(reader/'manifest.json'),
                        'reports_sha256': {name: digest(gates/(name+'.json')) for name in ['bridge', 'policy']}}
            write_json(gates/'complete.json', complete)
            self.assertTrue(check_gate(gates, reader))
            write_json(gates/'policy.json', {'passed': False, 'manifest_sha256': fingerprint(manifest)})
            with self.assertRaisesRegex(ValueError, 'Changed or failed'):
                check_gate(gates, reader)
            complete['passed'] = False
            write_json(gates/'complete.json', complete)
            with self.assertRaisesRegex(ValueError, 'did not pass'):
                check_gate(gates, reader)


if __name__ == '__main__':
    unittest.main()
