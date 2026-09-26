"""Read-only acceptance: recheck qualification and actual validation coverage."""
import argparse
import json
from pathlib import Path
from audit_hosted_coverage import verify_qualification
from collect_local_readers import execution_source
from contracts import fingerprint
from evaluate_reader_coverage import summarize
from smoke import digest, write_json
from validate_reader_gates import ready


def verify_coverage(reader, pilot, report_path, expected):
    manifest_path = reader/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest != expected:
        raise ValueError('Coverage execution differs from qualification')
    execution_source(manifest)
    pm = json.loads((pilot/'manifest.json').read_text())
    if pm['phase'] != 'validation' or pm['stage'] != 'coverage-pilot':
        raise ValueError('Only validation coverage qualifies a reader')
    if digest(pilot/'jobs.json') != pm['jobs_sha256']:
        raise ValueError('Pilot jobs changed')
    sources = {Path(path): sha for path, sha in pm['source_hashes'].items()}
    for path, sha in sources.items():
        if digest(path) != sha:
            raise ValueError('Pilot source changed')
    if not ready(reader, pilot, 'reader-coverage-pilot-jobs-complete.json'):
        raise ValueError('Coverage execution is incomplete')
    report = json.loads(report_path.read_text())
    if report['reader_manifest_sha256'] != digest(manifest_path) or report['pilot_manifest_sha256'] != digest(pilot/'manifest.json'):
        raise ValueError('Coverage report provenance differs')
    jobs = json.loads((pilot/'jobs.json').read_text())['jobs']
    ids = [job['request_id'] for job in jobs]
    if len(ids) != len(set(ids)) or set(ids) != set(report['result_sha256']):
        raise ValueError('Coverage request set differs')
    results = {}
    for job in jobs:
        rid = job['request_id']
        if rid != fingerprint({'system': job['system'], 'evidence': job['evidence']}):
            raise ValueError('Coverage request identity differs')
        path = reader/'results'/(rid+'.json')
        if digest(path) != report['result_sha256'][rid]:
            raise ValueError('Coverage result changed')
        results[rid] = json.loads(path.read_text())
        sources[path] = digest(path)
    actual = summarize(results, pm['strata'])
    if not actual['passed'] or any(report.get(key) != value for key, value in actual.items()):
        raise ValueError('Raw coverage fails or differs from report')
    for path in [manifest_path, pilot/'manifest.json', pilot/'jobs.json', report_path,
                 reader/'reader-coverage-pilot-jobs-complete.json']:
        sources[path] = digest(path)
    return {str(path.resolve()): sha for path, sha in sources.items()}


def main():
    p = argparse.ArgumentParser()
    for name in ['qualification-reader', 'gates', 'bridge', 'policy', 'coverage-reader', 'pilot', 'coverage-report', 'out']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('Preserve existing acceptance record')
    # Frozen 90-request development pilot shared by all candidate executions.
    if digest(a.pilot/'jobs.json') != 'ca9bc458bfc298a2c649c5de0e4bd0288fbe85c78de6a63f13bd88cbf7d8c441':
        raise ValueError('Acceptance requires the registered 90-request pilot')
    expected = json.loads((a.qualification_reader/'manifest.json').read_text())
    sources = verify_qualification(a.qualification_reader, a.gates, a.bridge, a.policy, expected)
    sources.update(verify_coverage(a.coverage_reader, a.pilot, a.coverage_report, expected))
    for name in ['verify_reader_acceptance.py', 'audit_hosted_coverage.py', 'collect_local_readers.py', 'evaluate_reader_coverage.py']:
        path = Path(__file__).with_name(name)
        sources[str(path.resolve())] = digest(path)
    write_json(a.out, {'passed': True, 'reader_manifest': expected,
        'source_hashes': sources, 'scope': 'Qualification and validation engineering coverage only. Not held-out detector performance or semantic faithfulness.'})


if __name__ == '__main__':
    main()
