"""Wait for both backed-up judge checks, evaluate fixed gates, and fail closed."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from contracts import fingerprint
from smoke import digest, write_json


def ready(reader, fixtures, completion_name):
    manifest_path = reader/'manifest.json'
    completion = reader/completion_name
    if not manifest_path.exists() or not completion.exists():
        return False
    manifest = json.loads(manifest_path.read_text())
    done = json.loads(completion.read_text())
    if done['manifest_sha256'] != fingerprint(manifest) or done['jobs_sha256'] != digest(fixtures/'jobs.json'):
        raise ValueError('Judge completion belongs to another execution or fixture set')
    jobs = json.loads((fixtures/'jobs.json').read_text())['jobs']
    for job in jobs:
        path = reader/'results'/(job['request_id']+'.json')
        if not path.exists():
            return False
        result = json.loads(path.read_text())
        if result['request_id'] != job['request_id'] or result['manifest_sha256'] != fingerprint(manifest):
            raise ValueError('Mixed judge-check results')
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reader', type=Path, required=True)
    p.add_argument('--bridge', type=Path, required=True)
    p.add_argument('--policy', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--hours', type=float, default=4)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + a.hours*3600
    checks = [('bridge', a.bridge, 'local-bridge-jobs-complete.json'),
              ('policy', a.policy, 'local-policy-check-jobs-complete.json')]
    while time.monotonic() < deadline:
        if all(ready(a.reader, fixtures, completion) for _, fixtures, completion in checks):
            break
        time.sleep(60)
    else:
        raise TimeoutError('Backed-up judge validation still pending')
    reports = {}
    for name, fixtures, _ in checks:
        out = a.out/(name+'.json')
        if out.exists():
            raise ValueError('Preserve existing gate report')
        subprocess.run([sys.executable, str(Path(__file__).with_name('evaluate_local_bridge.py')),
                        '--bridge', str(fixtures), '--reader', str(a.reader), '--out', str(out)], check=True)
        reports[name] = json.loads(out.read_text())
    passed = all(report['passed'] for report in reports.values())
    write_json(a.out/'complete.json', {'passed': passed, 'reader_manifest_sha256': digest(a.reader/'manifest.json'),
                                      'reports_sha256': {name: digest(a.out/(name+'.json')) for name in reports}})
    if not passed:
        raise SystemExit('Judge gate failed; downstream inference was not authorized by this controller')


if __name__ == '__main__':
    main()
