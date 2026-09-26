import json
import tempfile
import unittest
from pathlib import Path
from contracts import fingerprint
from evaluate_reader_coverage import summarize
from hosted_text_reader_escaped import execution_manifest
from smoke import digest, write_json
from verify_reader_acceptance import verify_coverage


class AcceptanceTest(unittest.TestCase):
    def fixture(self, root):
        reader=root/'reader';pilot=root/'pilot';(reader/'results').mkdir(parents=True);pilot.mkdir()
        manifest=execution_manifest('deepseek32escaped');write_json(reader/'manifest.json',manifest)
        request={'system':'fixture','evidence':{'text':'test'}};rid=fingerprint(request)
        write_json(pilot/'jobs.json',{'jobs':[{'request_id':rid,**request}]})
        pm={'phase':'validation','stage':'coverage-pilot','source_hashes':{},'jobs_sha256':digest(pilot/'jobs.json'),'strata':{'fixture':[rid]}}
        write_json(pilot/'manifest.json',pm)
        result={'request_id':rid,'manifest_sha256':fingerprint(manifest),'status':'ok','judgment':{'score':0,'confidence':'high'}}
        rp=reader/'results'/(rid+'.json');write_json(rp,result)
        write_json(reader/'reader-coverage-pilot-jobs-complete.json',{'jobs_sha256':pm['jobs_sha256'],'manifest_sha256':fingerprint(manifest)})
        report=summarize({rid:result},pm['strata']);report.update(reader_manifest_sha256=digest(reader/'manifest.json'),pilot_manifest_sha256=digest(pilot/'manifest.json'),result_sha256={rid:digest(rp)})
        path=root/'coverage.json';write_json(path,report)
        return reader,pilot,path,manifest

    def test_accepts_bound_outputs_and_rejects_changed_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp));self.assertTrue(verify_coverage(*args))
            rp=next((args[0]/'results').glob('*.json'));row=json.loads(rp.read_text());row['judgment']['score']=2;write_json(rp,row)
            with self.assertRaisesRegex(ValueError,'result changed'):verify_coverage(*args)

    def test_updated_hash_cannot_hide_failed_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp));rp=next((args[0]/'results').glob('*.json'));row=json.loads(rp.read_text());row['status']='unavailable';write_json(rp,row)
            report=json.loads(args[2].read_text());report['result_sha256'][row['request_id']]=digest(rp);write_json(args[2],report)
            with self.assertRaisesRegex(ValueError,'Raw coverage fails'):verify_coverage(*args)

    def test_test_phase_cannot_qualify_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp));p=args[1]/'manifest.json';pm=json.loads(p.read_text());pm['phase']='test';write_json(p,pm)
            with self.assertRaisesRegex(ValueError,'Only validation'):verify_coverage(*args)


if __name__=='__main__':unittest.main()
