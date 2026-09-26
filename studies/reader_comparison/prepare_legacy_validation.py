"""Prepare validation reviews after complete, gated local summary inference."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from contracts import fingerprint
from smoke import digest, write_json
from validate_reader_gates import ready


def check_gate(directory, reader):
    path = directory/'complete.json'
    if not path.exists():
        return False
    complete = json.loads(path.read_text())
    if not complete['passed']:
        raise ValueError('Local summarizer did not pass the registered reader checks')
    if complete['reader_manifest_sha256'] != digest(reader/'manifest.json'):
        raise ValueError('Gate applies to another reader execution')
    manifest = json.loads((reader/'manifest.json').read_text())
    for name, sha in complete['reports_sha256'].items():
        report_path = directory/(name+'.json')
        report = json.loads(report_path.read_text())
        if digest(report_path) != sha or not report['passed'] or report['manifest_sha256'] != fingerprint(manifest):
            raise ValueError('Changed or failed component gate')
    if set(complete['reports_sha256']) != {'bridge', 'policy'}:
        raise ValueError('Both registered checks are required')
    return True


def main():
    p = argparse.ArgumentParser()
    for name in ('repo', 'reader', 'gates', 'summary-jobs', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--hours', type=float, default=4)
    a = p.parse_args()
    prepared = json.loads((a.summary_jobs/'manifest.json').read_text())
    if (prepared.get('study'), prepared['dataset'], prepared['phase'], prepared['stage']) != ('archived-gptoss-local-extension-v1', 'fresh', 'validation', 'summaries'):
        raise ValueError('Only the separate fresh validation summary cohort is allowed')
    deadline = time.monotonic() + a.hours*3600
    while time.monotonic() < deadline:
        if check_gate(a.gates, a.reader) and ready(a.reader, a.summary_jobs, 'legacy-validation-summary-jobs-complete.json'):
            break
        time.sleep(30)
    else:
        raise TimeoutError('Complete gated validation summaries still pending')
    if a.out.exists():
        raise ValueError('Preserve existing validation preparation output')
    a.out.mkdir(parents=True)
    scripts = Path(__file__).parent
    summary = a.out/'summaries.json'
    commands = [
        [sys.executable, str(scripts/'collect_local_readers.py'), '--jobs', str(a.summary_jobs),
         '--readers', str(a.reader), '--out', str(summary)],
        [sys.executable, str(scripts/'legacy_local_jobs.py'), '--repo', str(a.repo), '--dataset', 'fresh',
         '--phase', 'validation', '--stage', 'reviews', '--summaries', str(summary), '--out', str(a.out/'reviews')]]
    for index, command in enumerate(commands):
        with (a.out/f'stage-{index}.log').open('w') as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    files = [summary, a.out/'reviews/manifest.json', a.out/'reviews/jobs.json', a.out/'reviews/aliases.json',
             a.gates/'complete.json', Path(__file__)]
    write_json(a.out/'complete.json', {'phase': 'validation', 'commands': commands,
                                     'source_hashes': {str(path.resolve()): digest(path) for path in files},
                                     'scope': 'Prepared inputs only; no held-out labels read and no review inference dispatched.'})
    print(json.dumps({'prepared_validation_reviews': str(a.out/'reviews')}), flush=True)


if __name__ == '__main__':
    main()
