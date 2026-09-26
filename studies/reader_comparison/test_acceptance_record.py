import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contracts import fingerprint
from hosted_text_reader_direct import execution_manifest
from smoke import digest,write_json
from verify_reader_acceptance import load_acceptance


class AcceptanceRecordTest(unittest.TestCase):
    def test_recomputes_both_gates_and_rejects_omitted_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.json';source.write_text('{}')
            manifest=execution_manifest('deepseek32direct');pilot=root/'pilot';pilot.mkdir();(pilot/'jobs.json').write_text('{}')
            names=['qualification_reader','gates','bridge','policy','coverage_reader','pilot','coverage_report']
            record={'kind':'validated-reader-acceptance-v1','passed':True,'reader_manifest':manifest,'inputs':{n:str(root/n) for n in names},'source_hashes':{str(source):digest(source)}}
            out=root/'acceptance.json';write_json(out,record)
            original_digest=digest
            def controlled_digest(path):
                if Path(path)==pilot/'jobs.json':return 'ca9bc458bfc298a2c649c5de0e4bd0288fbe85c78de6a63f13bd88cbf7d8c441'
                return original_digest(path)
            with patch('verify_reader_acceptance.digest',side_effect=controlled_digest),patch('verify_reader_acceptance.verify_qualification',return_value={str(source):digest(source)}) as qualification,patch('verify_reader_acceptance.verify_coverage',return_value={str(source):digest(source)}) as coverage:
                self.assertIn(str(out.resolve()),load_acceptance(out,manifest));qualification.assert_called_once();coverage.assert_called_once()
                record['source_hashes']={};write_json(out,record)
                with self.assertRaisesRegex(ValueError,'omits actual gate sources'):load_acceptance(out,manifest)

    def test_pass_flag_cannot_replace_manifest_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'a.json';write_json(path,{'kind':'validated-reader-acceptance-v1','passed':True,'reader_manifest':{}})
            with self.assertRaisesRegex(ValueError,'identity differs'):load_acceptance(path,execution_manifest('deepseek32direct'))
