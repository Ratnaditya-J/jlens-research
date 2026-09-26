import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_comparison_casebook import main, fixed_selection, fenced
from collect_local_readers import aggregate
from contracts import fingerprint
from interpret_readers import ARMS
from local_reader_jobs import review_jobs
from smoke import digest, write_json


class CasebookTests(unittest.TestCase):
    def test_selection_is_order_independent_and_excludes_missing(self):
        rows = [{'episode_id': str(i), 'label': 1, 'condition': 'prohibited',
                 'scores': {'raw_probe': 1, 'j_summary_context': 0, 'oracle_context': 0}} for i in range(8)]
        thresholds = dict(raw_probe=.5, j_summary_context=1, oracle_context=1)
        expected = fixed_selection(rows, thresholds)
        rows.append({'episode_id': 'missing', 'label': 1, 'condition': 'prohibited', 'scores': {}})
        self.assertEqual(fixed_selection(list(reversed(rows)), thresholds), expected)
        self.assertEqual(len(expected[0]['ids']), 3)
        self.assertEqual(expected[0]['flags'], ['raw_probe'])

    def test_untrusted_markdown_cannot_close_fence(self):
        text = fenced({'description': '```\n# pretend instruction\n````'})
        self.assertTrue(text.startswith('`````json\n'))
        self.assertTrue(text.endswith('\n`````'))

    def test_complete_provenance_chain_and_tampered_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for sub in ['jobs', 'interpretations', 'report', 'r0/results', 'r1/results']:
                (root/sub).mkdir(parents=True)
            rows = [{'episode_id': str(i), 'family_id': 'fixture', 'split': 'test',
                     'prefix_sha256': str(i), 'prefix_text': 'prefix ' + str(i),
                     'endpoint': 'before_action', 'position_in_generated_output': False,
                     'j_tokens': [{'layer': 20, 'tokens': ['audit'], 'scores': [1.], 'token_ids': [42]}],
                     'oracle': [{'layer': 20, 'status': 'ok', 'text': 'checking audit', 'truncated': False}]}
                    for i in range(2)]
            bundle = {'rows': rows, 'subject_identity': 'fixture', 'endpoint': 'before_action'}
            write_json(root/'bundle.json', bundle)
            summaries = {'bundle_sha256': digest(root/'bundle.json'), 'phase': 'test',
                         'summaries': {str(i): {'20': 'audit concept'} for i in range(2)}}
            write_json(root/'summaries.json', summaries)
            jobs, aliases, donors = review_jobs(rows, summaries['summaries'])
            jobs.sort(key=lambda r: r['request_id'])
            write_json(root/'jobs/jobs.json', {'jobs': jobs})
            write_json(root/'jobs/aliases.json', aliases)
            prepared = {'phase': 'test', 'stage': 'reviews', 'arms': ARMS, 'donors': donors,
                        'bundle_sha256': digest(root/'bundle.json'), 'summaries_sha256': digest(root/'summaries.json'),
                        'jobs_sha256': digest(root/'jobs/jobs.json'), 'aliases_sha256': digest(root/'jobs/aliases.json')}
            write_json(root/'jobs/manifest.json', prepared)
            manifests, results = [], []
            for i in range(2):
                manifest = {'model': {'family': ['gptoss', 'qwen'][i]}}
                manifests.append(manifest)
                write_json(root/f'r{i}/manifest.json', manifest)
                result = {}
                for job in jobs:
                    rid = job['request_id']
                    result[rid] = {'request_id': rid, 'manifest_sha256': fingerprint(manifest), 'status': 'ok',
                                   'judgment': {'score': i, 'confidence': 'high'}, 'raw_response': 'fixture'}
                    write_json(root/f'r{i}/results/{rid}.json', result[rid])
                results.append(result)
            scores = aggregate(aliases, results)
            protocol = {'readers': manifests}
            im = {**prepared, 'reader_protocol': protocol}
            write_json(root/'interpretations/manifest.json', im)
            write_json(root/'interpretations/scores.json', scores)
            write_json(root/'interpretations/complete.json', {'manifest_sha256': fingerprint(im),
                       'scores_sha256': digest(root/'interpretations/scores.json')})
            thresholds = {arm: 1 for arm in ARMS}
            thresholds.update(raw_probe=.5, jspace_probe=.5, text_probe=.5)
            lock = {'identity': 'fixture', 'endpoint': 'before_action', 'thresholds': thresholds,
                    'reader_protocol_sha256': fingerprint(protocol)}
            write_json(root/'lock.json', lock)
            cases = [{'episode_id': str(i), 'condition': 'prohibited', 'label': i,
                      'scores': {**{arm: 0 for arm in ARMS}, 'raw_probe': 1, 'jspace_probe': .8, 'text_probe': .1}}
                     for i in range(2)]
            write_json(root/'report/cases.json', cases)
            write_json(root/'report/summary.json', {'lock_sha256': digest(root/'lock.json'), 'identity': 'fixture',
                       'endpoint': 'before_action', 'casebook_selection': fixed_selection(cases, thresholds)})
            args = ['casebook']
            for name, value in [('report', 'report'), ('lock', 'lock.json'), ('bundle', 'bundle.json'),
                                ('summaries', 'summaries.json'), ('jobs', 'jobs'), ('interpretations', 'interpretations'), ('out', 'out')]:
                args += ['--' + name, str(root/value)]
            args += ['--readers', str(root/'r0'), str(root/'r1')]
            with patch.object(sys, 'argv', args):
                main()
            artifact = json.loads((root/'out/casebook.json').read_text())
            self.assertEqual(len(artifact['cases']), 2)
            self.assertIsNone(artifact['cases'][0]['manual_fidelity_assessment'])
            self.assertEqual(len(artifact['cases'][0]['reviews']), len(ARMS))
            cases[0]['scores']['context_only'] = 2
            write_json(root/'report/cases.json', cases)
            with patch.object(sys, 'argv', args), self.assertRaisesRegex(ValueError, 'Reported case scores differ'):
                main()


if __name__ == '__main__':
    unittest.main()
