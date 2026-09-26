"""Wait for verified local readouts, then prepare validation without test scoring."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from contracts import fingerprint
from smoke import digest, write_json

ENDPOINTS = ['before_action', 'during_action', 'after_action', 'end_prompt', 'before_action_32', 'before_action_64']


def ready(captures, jread, oracle):
    if not (jread/'manifest.json').exists() or not (oracle/'manifest.json').exists():
        return False
    jm = json.loads((jread/'manifest.json').read_text())
    if jm['n_fit_prompts'] != 32:
        raise ValueError('Primary analysis requires the registered32-passage lens')
    for source in captures.glob('*/complete.json'):
        d = jread/source.parent.name
        if not (d/'complete.json').exists():
            return False
        done = json.loads((d/'complete.json').read_text())
        if done['manifest_sha256'] != fingerprint(jm):
            raise ValueError('Mixed readout manifests')
        for name, key in [('jspace.safetensors', 'jspace_sha256'), ('readouts.json', 'readouts_sha256')]:
            if not (d/name).exists() or digest(d/name) != done[key]:
                return False  # Collector may still be copying this endpoint.
    om = json.loads((oracle/'manifest.json').read_text())
    actual = []
    for path in oracle.glob('batch-*.json'):
        batch = json.loads(path.read_text())
        if batch['request']['manifest_sha256'] != fingerprint(om) or fingerprint(batch['request']) != batch['request_sha256']:
            raise ValueError('Oracle batch provenance differs')
        actual.extend(row['cell_id'] for row in batch['results'])
    return len(actual) == len(set(actual)) and set(actual) == set(om['ordered_cell_ids'])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--runs', type=Path, required=True)
    p.add_argument('--logs', type=Path, required=True)
    p.add_argument('--hours', type=float, default=4)
    p.add_argument('--poll-seconds', type=float, default=120)
    a = p.parse_args()
    a.runs = a.runs.resolve()
    a.logs.mkdir(parents=True, exist_ok=True)
    captures = a.runs/'production-captures'
    if len(list(captures.glob('*/complete.json'))) != 509:
        raise ValueError('Incomplete registered capture bank')
    scripts = Path(__file__).parent
    pending = ENDPOINTS.copy()
    deadline = time.monotonic() + a.hours*3600
    while pending and time.monotonic() < deadline:
        for endpoint in pending.copy():
            marker = a.logs/(endpoint+'-prepared.json')
            if marker.exists():
                record = json.loads(marker.read_text())
                for path, sha in record['output_sha256'].items():
                    if digest(path) != sha:
                        raise ValueError('Prepared validation artifact changed')
                pending.remove(endpoint)
                continue
            jread = a.runs/('jread-'+endpoint)
            oracle = a.runs/('oracle-'+endpoint)
            if not ready(captures, jread, oracle):
                continue
            features = a.runs/('features-'+endpoint)
            probes = a.runs/('probes-'+endpoint)
            bundle = a.runs/('bundle-'+endpoint+'.json')
            jobs = a.runs/('local-summary-validation-'+endpoint)
            rawprobe = a.runs/('early-raw-probe' if endpoint == 'before_action' else 'early-raw-probe-'+endpoint)/'raw-probe.json'
            commands = [
                ('assemble_features.py', ['--captures', captures, '--jspace', jread, '--audits', a.runs/'production-audits/audits.json', '--out', features, '--endpoint', endpoint]),
                ('rebind_raw_probe.py', ['--early-features', a.runs/('raw-'+endpoint), '--joint-features', features, '--early-probe', rawprobe, '--out', probes/'raw-probe.json']),
                ('probes.py', ['--manifest', features/'manifest.json', '--features', features/'features.npz', '--endpoint', endpoint, '--out', probes, '--arms', 'jspace']),
                ('assemble_bundle.py', ['--captures', captures, '--jlens', jread, '--oracle', oracle, '--endpoint', endpoint, '--out', bundle]),
                ('local_reader_jobs.py', ['--bundle', bundle, '--phase', 'validation', '--stage', 'summaries', '--out', jobs]),
            ]
            if features.exists() or probes.exists() or bundle.exists() or jobs.exists():
                raise ValueError('Partial or preexisting endpoint analysis needs inspection: ' + endpoint)
            with (a.logs/(endpoint+'.log')).open('w') as log:
                for script, args in commands:
                    subprocess.run([sys.executable, str(scripts/script), *map(str, args)], check=True, stdout=log, stderr=log)
            outputs = [features/'manifest.json', features/'features.npz', probes/'raw-probe.json', probes/'jspace-probe.json', bundle, jobs/'manifest.json', jobs/'jobs.json', jobs/'aliases.json']
            write_json(marker, {'endpoint': endpoint, 'code_sha256': digest(__file__),
                                'output_sha256': {str(path): digest(path) for path in outputs},
                                'scope': 'Training and validation preparation only. Test labels do not enter fitting or thresholds; test trajectories are not scored.'})
            pending.remove(endpoint)
            print(json.dumps({'prepared': endpoint, 'pending': pending}), flush=True)
        if pending:
            time.sleep(a.poll_seconds)
    if pending:
        raise TimeoutError('Readouts still pending: ' + ', '.join(pending))


if __name__ == '__main__':
    main()
