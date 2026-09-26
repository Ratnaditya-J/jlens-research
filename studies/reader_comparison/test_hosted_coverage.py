import json
import tempfile
import unittest
from pathlib import Path

from audit_hosted_coverage import verify_qualification, activate_coverage_budget
from contracts import fingerprint
from evaluate_local_bridge import evaluate
from hosted_text_reader import execution_manifest
from smoke import digest, write_json


class HostedCoverageTest(unittest.TestCase):
    def test_uncertain_prior_charge_remains_reserved_and_reduces_available_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json'
            prior={'status':'paused_after_reader_audit','additional_limit_usd':1,
                   'spent_microusd':100000,'reserved_microusd':300000,
                   'records':{'old':{'status':'reserved','reserved_microusd':300000,'request_sha256':'uncertain'}}}
            plan={'request_allowlist':['new'],'maximum_reserved_microusd':700000,'scope':'test'}
            write_json(path,prior); before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'carrying prior uncertain'):
                activate_coverage_budget(path,plan)
            self.assertEqual(path.read_bytes(),before)
            plan['maximum_reserved_microusd']=400000
            activate_coverage_budget(path,plan)
            active=json.loads(path.read_text())
            self.assertEqual(active['records'],prior['records'])
            self.assertEqual(active['reserved_microusd'],300000)
            self.assertEqual(active['spent_microusd'],100000)
            self.assertEqual(active['additional_limit_usd'],1)
            write_json(path,prior)
            with self.assertRaisesRegex(ValueError,'already attempted'):
                activate_coverage_budget(path,{**plan,'request_allowlist':['uncertain']})

    def fixture(self, root):
        reader=root/'reader'; gates=root/'gates'
        (reader/'results').mkdir(parents=True); gates.mkdir()
        manifest=execution_manifest('deepseek32'); write_json(reader/'manifest.json',manifest)
        jobs=[]; references=[]; results={}
        for score in [0,2]:
            payload={'system':'test','evidence':{'synthetic_score':score}}
            rid=fingerprint(payload); jobs.append({'request_id':rid,**payload})
            references.append({'request_id':rid,'reference_score':score})
            result={'request_id':rid,'manifest_sha256':fingerprint(manifest),'status':'ok',
                    'judgment':{'score':score,'confidence':'high'}}
            results[rid]=result; write_json(reader/'results'/(rid+'.json'),result)
        fixtures=[]
        for name,completion in [('bridge','local-bridge-jobs-complete.json'),('policy','local-policy-check-jobs-complete.json')]:
            directory=root/name; directory.mkdir(); fixtures.append(directory)
            write_json(directory/'jobs.json',{'jobs':jobs});write_json(directory/'references.json',{'references':references})
            write_json(directory/'protocol.json',{'jobs_sha256':digest(directory/'jobs.json'),
                'references_sha256':digest(directory/'references.json'),'valid_json_fraction_min':.9,
                'exact_reference_agreement_fraction_min':.9,'minimum_score_recall':{'0':1,'2':1}})
            write_json(reader/completion,{'jobs_sha256':digest(directory/'jobs.json'),'manifest_sha256':fingerprint(manifest)})
            report=evaluate(references,results,fingerprint(manifest))
            report.update(passed=True,manifest_sha256=fingerprint(manifest),protocol_sha256=digest(directory/'protocol.json'))
            write_json(gates/(name+'.json'),report)
        write_json(gates/'complete.json',{'passed':True,'reader_manifest_sha256':digest(reader/'manifest.json'),
                   'reports_sha256':{name:digest(gates/(name+'.json')) for name in ['bridge','policy']}})
        return reader,gates,*fixtures,manifest

    def test_binds_outputs_and_rejects_raw_failure_behind_cached_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp))
            sources=verify_qualification(*args)
            result_path=next((args[0]/'results').glob('*.json'))
            self.assertEqual(sources[str(result_path.resolve())],digest(result_path))
            data=json.loads(result_path.read_text()); data['judgment']['score']=1
            write_json(result_path,data)
            with self.assertRaisesRegex(ValueError,'Raw qualification judgments fail'):
                verify_qualification(*args)

    def test_changed_execution_or_incomplete_outputs_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader,gates,bridge,policy,manifest=self.fixture(Path(tmp))
            with self.assertRaisesRegex(ValueError,'execution differs'):
                verify_qualification(reader,gates,bridge,policy,{**manifest,'temperature':1})
            next((reader/'results').glob('*.json')).unlink()
            with self.assertRaisesRegex(ValueError,'incomplete'):
                verify_qualification(reader,gates,bridge,policy,manifest)


if __name__=='__main__':unittest.main()
