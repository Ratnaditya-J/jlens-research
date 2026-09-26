"""Exercise alternate-family collection and refusal paths through the actual CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contracts import fingerprint
from smoke import digest, write_json
from interpret_readers import ARMS

SCRIPTS=Path(__file__).resolve().parent

class MistralProtocolTest(unittest.TestCase):
    def fixture(self, root, second_family='mistral'):
        jobs=root/'jobs';jobs.mkdir()
        request={'system':'synthetic test rubric','evidence':{'synthetic':'test'}}
        rid=fingerprint(request)
        write_json(jobs/'jobs.json',{'jobs':[{'request_id':rid,**request}]})
        write_json(jobs/'aliases.json',[{'episode_id':'fixture','arm':a,'request_id':rid} for a in ARMS])
        readers=[];bridge=[];policy=[];manifests=[]
        for family,source in [('gptoss','local_text_reader.py'),(second_family,'local_text_reader_mistral.py')]:
            reader=root/family;(reader/'results').mkdir(parents=True)
            manifest={'model':{'family':family},'code_sha256':digest(SCRIPTS/source)}
            if second_family == 'deepseek':
                from hosted_text_reader import execution_manifest as pair_manifest
                from hosted_text_reader_medium import execution_manifest as medium_manifest
                manifest = medium_manifest('gptoss20medium') if family == 'gptoss' else pair_manifest('deepseek32')
            write_json(reader/'manifest.json',manifest)
            write_json(reader/'results'/f'{rid}.json',{'request_id':rid,'manifest_sha256':fingerprint(manifest),'status':'ok','judgment':{'score':2,'confidence':'high'}})
            for name, paths in [('bridge',bridge),('policy',policy)]:
                path=root/f'{family}-{name}.json';write_json(path,{'passed':True,'manifest_sha256':fingerprint(manifest)});paths.append(path)
            readers.append(reader);manifests.append(manifest)
        summary=root/'summaries.json';write_json(summary,{'summarizer_manifest':manifests[1]})
        write_json(jobs/'manifest.json',{'stage':'reviews','phase':'validation','arms':ARMS,'jobs_sha256':digest(jobs/'jobs.json'),'aliases_sha256':digest(jobs/'aliases.json'),'summaries_sha256':digest(summary)})
        command=[sys.executable,str(SCRIPTS/'collect_local_readers.py'),'--jobs',str(jobs),'--readers',*map(str,readers),'--bridge-reports',*map(str,bridge),'--policy-check-reports',*map(str,policy),'--summaries',str(summary),'--second-reader-family',second_family,'--out',str(root/'out')]
        return command,bridge,policy,summary

    def test_explicit_protocol_and_exact_summary_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);command,_,_,_=self.fixture(root)
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            manifest=json.loads((root/'out/manifest.json').read_text())
            self.assertEqual(manifest['reader_protocol']['kind'],'local-two-reader-mistral-v1')
            self.assertEqual(manifest['reader_protocol_sha256'],fingerprint(manifest['reader_protocol']))
            scores=json.loads((root/'out/scores.json').read_text())
            self.assertTrue(all(scores[0][arm]['reviewer_scores']==[2,2] for arm in ARMS))

    def test_hosted_deepseek_protocol_binds_both_transports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);command,_,_,_=self.fixture(root,second_family='deepseek')
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            manifest=json.loads((root/'out/manifest.json').read_text())
            self.assertEqual(manifest['reader_protocol']['kind'],'hosted-two-reader-deepseek-v1')
            for name in ['budgeted_api_client.py','budgeted_hosted_medium.py','literal_evidence.py']:
                self.assertEqual(manifest['source_hashes'][str((SCRIPTS/name).resolve())],digest(SCRIPTS/name))
            self.assertIn('cannot be hash-pinned',manifest['reader_protocol']['hosting_limit'])

    def test_failed_gate_and_wrong_execution_fail_closed(self):
        for failure in ['failed_bridge','wrong_policy_execution','wrong_family','wrong_summary_execution']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);command,bridge,policy,summary=self.fixture(root)
                if failure=='failed_bridge':
                    p=bridge[1];data=json.loads(p.read_text());data['passed']=False;write_json(p,data)
                elif failure=='wrong_policy_execution':
                    p=policy[1];data=json.loads(p.read_text());data['manifest_sha256']='wrong';write_json(p,data)
                elif failure=='wrong_family':
                    command[command.index('--second-reader-family')+1]='qwen'
                else:
                    data=json.loads(summary.read_text());data['summarizer_manifest']['model']['family']='qwen';write_json(summary,data)
                    p=root/'jobs/manifest.json';data=json.loads(p.read_text());data['summaries_sha256']=digest(summary);write_json(p,data)
                result=subprocess.run(command,capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse((root/'out/complete.json').exists())

if __name__=='__main__':unittest.main()
