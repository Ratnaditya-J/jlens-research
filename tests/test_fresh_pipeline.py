"""Synthetic integration evidence only; never experimental observations."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))

class FreshPipeline(unittest.TestCase):
    def test_calibration_isolation_and_heldout_accounting(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ['scripts/calibrate_fresh.py', 'scripts/evaluate_fresh.py',
                         'scripts/paired_breakdown.py', 'scripts/supervised_jspace.py', 'scripts/probe_latency.py', 'scripts/review_latency.py', 'src/thresholds.py', 'src/comparison_diagnostics.py']:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dest)
            for name in ['configs/final-protocol.json', 'configs/supervised-jspace.json', 'manifests/fresh-splits.json',
                         'runs/fresh-assembled/manifest.json']:
                write(root / name, {'synthetic': True})
            write(root / 'configs/random-direction-control.json', {'seed':20260919,'count':20})
            data = root / 'runs/fresh-assembled'
            for split in ['train', 'validation', 'test']:
                rows, contexts, judgments, vectors = [], [], [], []
                for family in range(8):
                    for label in range(2):
                        eid = f'{split}-{family}-{label}'
                        rows.append({'episode_id': eid, 'family_id': f'{split}-{family}',
                                     'label': 'misaligned' if label else 'benign',
                                     'feature_index': len(vectors), 'template': 'synthetic',
                                     'control': None, 'runtime_use_cache': False})
                        vectors.append([label * 2 - 1, family / 10])
                        contexts.append({'episode_id': eid, 'prompt': 'synthetic malicious' if label else 'synthetic benign', 'generated_prefix': 'prefix'})
                        judgments.append({'episode_id': eid, 'jview': {'score': 2 if label and family % 2 else 0}, 'context_only': {'score': 2 * label}})
                write(data / (split + '-records.json'), rows)
                write(data / (split + '-contexts.json'), {'rows': contexts})
                np.savez(data / (split + '-features.npz'), **{f'layer_{l}': np.array(vectors) for l in [7, 15, 21, 22]})
                np.savez(data / (split + '-jspace-features.npz'), **{f'layer_{l}': np.array(vectors) * 2 for l in [7,15,21,22]})
                jd = root / f'runs/fresh-jview-{split}'
                write(jd / 'scores.json', judgments)
                write(jd / 'complete.json', {'errors': [], 'scores_sha256': hashlib.sha256((jd / 'scores.json').read_bytes()).hexdigest()})
            write(data / 'manifest.json', {'files_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data.iterdir() if p.name != 'manifest.json'}})
            # Calibration must succeed with all test inputs entirely inaccessible.
            hidden = root / 'hidden-test'
            hidden.mkdir()
            for p in data.glob('test-*'):
                p.rename(hidden / p.name)
            def run(script, *args):
                return subprocess.run([sys.executable, str(root / 'scripts' / script), *args], capture_output=True, text=True)
            secondary = run('supervised_jspace.py', 'calibrate')
            self.assertEqual(secondary.returncode, 0, secondary.stderr)
            first = run('calibrate_fresh.py')
            self.assertEqual(first.returncode, 0, first.stderr)
            lock = root / 'runs/fresh-calibration/lock.json'
            before = lock.read_bytes()
            self.assertNotEqual(run('calibrate_fresh.py').returncode, 0)
            self.assertEqual(lock.read_bytes(), before)
            for p in hidden.iterdir():
                p.rename(data / p.name)
            secondary = run('supervised_jspace.py', 'evaluate')
            self.assertEqual(secondary.returncode, 0, secondary.stderr)
            scored = run('evaluate_fresh.py')
            self.assertEqual(scored.returncode, 0, scored.stderr)
            report = json.loads((root / 'reports/final-comparison/summary.json').read_text())
            self.assertEqual(report['confirmed_four_way'], {'probe_only': 4, 'jlens_only': 0, 'both': 4, 'neither': 8})
            self.assertEqual(report['confirmed_paired_n'], 16)
            self.assertEqual(len(report['random_direction_diagnostics']['directions']), 20)
            self.assertIn('fpr_difference', report['cluster_intervals'])
            timing = run('probe_latency.py')
            self.assertEqual(timing.returncode, 0, timing.stderr)
            self.assertEqual(json.loads((root / 'reports/probe-latency-primary.json').read_text())['repetitions'], 1000)
            primary_report = root / 'reports/final-comparison/summary.json'
            original_primary = primary_report.read_bytes()
            shutil.copytree(data, root / 'runs/template-challenge-assembled')
            shutil.copytree(root / 'runs/fresh-jview-test', root / 'runs/template-challenge-jview-test')
            challenge = run('evaluate_fresh.py', '--dataset', 'template-challenge')
            self.assertEqual(challenge.returncode, 0, challenge.stderr)
            self.assertEqual(primary_report.read_bytes(), original_primary)
            self.assertEqual(lock.read_bytes(), before)
            challenged = json.loads((root / 'reports/template-challenge-comparison/summary.json').read_text())
            self.assertEqual(challenged['confirmed_four_way'], report['confirmed_four_way'])
            self.assertEqual(challenged['dataset'], 'template-challenge')
            # Earlier endpoints have isolated training/locks/reports, with no test access in calibration.
            earlier = root / 'runs/fresh-offset32-assembled'
            shutil.copytree(data, earlier)
            for phase in ['validation', 'test']:
                shutil.copytree(root / f'runs/fresh-jview-{phase}', root / f'runs/fresh-offset32-jview-{phase}')
            for p in earlier.glob('test-*'):
                p.rename(hidden / p.name)
            offset_cal = run('calibrate_fresh.py', '--offset', '32')
            self.assertEqual(offset_cal.returncode, 0, offset_cal.stderr)
            for p in hidden.iterdir():
                p.rename(earlier / p.name)
            offset_eval = run('evaluate_fresh.py', '--offset', '32')
            self.assertEqual(offset_eval.returncode, 0, offset_eval.stderr)
            offset_report = json.loads((root / 'reports/final-comparison-offset32/summary.json').read_text())
            self.assertEqual(offset_report['confirmed_four_way'], report['confirmed_four_way'])
            self.assertEqual(offset_report['offset_before_code_onset'], 32)
            self.assertEqual(primary_report.read_bytes(), original_primary)
            self.assertEqual(lock.read_bytes(), before)
            # A changed held-out tensor must fail assembled-artifact integrity.
            tensor = data / 'test-features.npz'
            original = tensor.read_bytes()
            tensor.write_bytes(original + b'changed')
            self.assertNotEqual(run('evaluate_fresh.py').returncode, 0)
            tensor.write_bytes(original)
            # Mutating a calibration source after locking must be rejected.
            write(data / 'validation-records.json', [])
            self.assertNotEqual(run('evaluate_fresh.py').returncode, 0)

if __name__ == '__main__':
    unittest.main()
