"""Collect local reader outputs with explicit missingness and frozen provenance."""
import argparse
import json
from pathlib import Path
from contracts import fingerprint
from interpret_readers import ARMS
from smoke import digest, write_json


def load_jobs(directory):
    manifest = json.loads((directory/'manifest.json').read_text())
    for path, sha in manifest.get('source_hashes', {}).items():
        if digest(path) != sha:
            raise ValueError('Prepared reader source changed')
    for name in ('jobs', 'aliases'):
        if digest(directory/(name+'.json')) != manifest[name+'_sha256']:
            raise ValueError('Prepared reader input changed: ' + name)
    jobs = json.loads((directory/'jobs.json').read_text())['jobs']
    for job in jobs:
        if fingerprint({'system': job['system'], 'evidence': job['evidence']}) != job['request_id']:
            raise ValueError('Request content changed')
    aliases = json.loads((directory/'aliases.json').read_text())
    ids = {job['request_id'] for job in jobs}
    if any(a.get('request_id') is not None and a['request_id'] not in ids for a in aliases):
        raise ValueError('Alias references unknown request')
    return manifest, jobs, aliases


def load_results(directory, jobs):
    manifest = json.loads((directory/'manifest.json').read_text())
    sha = fingerprint(manifest)
    results = {}
    for job in jobs:
        request_id = job['request_id']
        path = directory/'results'/(request_id+'.json')
        if not path.exists():
            continue
        result = json.loads(path.read_text())
        if result.get('request_id') != request_id or result.get('manifest_sha256') != sha:
            raise ValueError('Reader result identity or execution changed')
        results[request_id] = result
    return manifest, results


def valid_score(result):
    if not result or result.get('status') != 'ok':
        return None
    judgment = result.get('judgment', {})
    score = judgment.get('score')
    if type(score) is not int or score not in (0, 1, 2) or judgment.get('confidence') not in ('high', 'medium', 'low'):
        return None
    return score


def execution_source(manifest):
    candidates = [Path(__file__).with_name(name) for name in
                  ('local_text_reader.py', 'local_text_reader_reasoning.py')]
    matches = [path for path in candidates if path.exists() and digest(path) == manifest['code_sha256']]
    if len(matches) != 1:
        raise ValueError('Reader execution source is missing or differs from its recorded hash')
    return matches[0]


def aggregate(aliases, readers, arms=ARMS):
    rows = {}
    for alias in aliases:
        row = rows.setdefault(alias['episode_id'], {'episode_id': alias['episode_id']})
        request_id = alias['request_id']
        scores = [valid_score(results.get(request_id)) for results in readers]
        row[alias['arm']] = {'score': min(scores) if all(s is not None for s in scores) else None,
                             'missing': any(s is None for s in scores), 'reviewer_scores': scores,
                             'request_sha256': [request_id]*len(readers)}
    if any(set(row)-{'episode_id'} != set(arms) for row in rows.values()):
        raise ValueError('Incomplete arm aliases')
    return list(rows.values())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--jobs', type=Path, required=True)
    p.add_argument('--readers', type=Path, nargs='+', required=True)
    p.add_argument('--bridge-reports', type=Path, nargs='*', default=[])
    p.add_argument('--policy-check-reports', type=Path, nargs='*', default=[])
    p.add_argument('--summaries', type=Path)
    p.add_argument('--lock', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    prepared, jobs, aliases = load_jobs(a.jobs)
    pairs = [load_results(reader, jobs) for reader in a.readers]
    source_files = [a.jobs/'manifest.json', a.jobs/'jobs.json', a.jobs/'aliases.json', Path(__file__),
                    Path(__file__).with_name('local_text_reader.py'), Path(__file__).with_name('local_reader_jobs.py'),
                    Path(__file__).with_name('interpret_readers.py'), Path(__file__).with_name('contracts.py')]
    source_files.extend(reader/'manifest.json' for reader in a.readers)
    source_files.extend(execution_source(manifest) for manifest, _ in pairs)
    source_files.extend(Path(path) for path in prepared.get('source_hashes', {}))
    if prepared.get('study') == 'archived-gptoss-local-extension-v1':
        source_files.append(Path(__file__).with_name('legacy_local_jobs.py'))
    source_files.extend(reader/'results'/(job['request_id']+'.json')
                        for reader in a.readers for job in jobs
                        if (reader/'results'/(job['request_id']+'.json')).exists())
    if prepared['stage'] == 'summaries':
        if len(pairs) != 1:
            raise ValueError('Exactly one registered summarizer required')
        manifest, results = pairs[0]
        if manifest['model']['family'] != 'qwen':
            raise ValueError('Registered summarizer must be Qwen base')
        summaries, missing = {}, []
        for alias in aliases:
            result = results.get(alias['request_id'], {})
            judgment = result.get('judgment', {})
            text = judgment.get('interpretation')
            if result.get('status') != 'ok' or set(judgment) != {'interpretation'} or not isinstance(text, str) or not text.strip():
                missing.append(alias)
                continue
            summaries.setdefault(alias['episode_id'], {})[str(alias['layer'])] = text
        write_json(a.out, {'bundle_sha256': prepared['bundle_sha256'], 'phase': prepared['phase'],
                           'summaries': summaries, 'missing': missing, 'summarizer_manifest': manifest,
                           'source_hashes': {str(path.resolve()): digest(path) for path in source_files}})
        return
    if len(pairs) != 2 or len(a.bridge_reports) != 2 or len(a.policy_check_reports) != 2 or not a.summaries:
        raise ValueError('Two validated readers and the original summary artifact are required')
    if digest(a.summaries) != prepared['summaries_sha256']:
        raise ValueError('Summary artifact changed')
    manifests = [pair[0] for pair in pairs]
    if [m['model']['family'] for m in manifests] != ['gptoss', 'qwen']:
        raise ValueError('Registered reviewer order is GPT-OSS, then Qwen')
    reports = [json.loads(path.read_text()) for path in a.bridge_reports]
    for report, manifest in zip(reports, manifests):
        if not report['passed'] or report['manifest_sha256'] != fingerprint(manifest):
            raise ValueError('Reader has not passed the bridge with this exact execution')
    for path, manifest in zip(a.policy_check_reports, manifests):
        report = json.loads(path.read_text())
        if not report['passed'] or report['manifest_sha256'] != fingerprint(manifest):
            raise ValueError('Reader has not passed the predefined policy check with this execution')
    summary = json.loads(a.summaries.read_text())
    if summary['summarizer_manifest'] != manifests[1]:
        raise ValueError('Summary execution must match the registered Qwen reader')
    protocol = {'kind': 'local-two-reader-v1', 'readers': manifests,
                'bridge_report_sha256': [digest(path) for path in a.bridge_reports],
                'policy_check_report_sha256': [digest(path) for path in a.policy_check_reports],
                'summarizer_manifest': summary['summarizer_manifest'],
                'collector_code_sha256': digest(__file__),
                'rule': 'Minimum of two valid ordinal scores; unavailable otherwise. Both individual scores retained.',
                'dependency': ('GPT-OSS first judge shares the archived subject base family; Qwen provides the summarizer and second judge. Original premium judgments remain separate.' if prepared.get('study') == 'archived-gptoss-local-extension-v1' else 'Qwen summarizer and second judge share a base family with the Oracle verbalizer; GPT-OSS is the independent-family judge.')}
    if prepared['phase'] == 'test':
        if not a.lock:
            raise ValueError('Locked validation protocol required')
        lock = json.loads(a.lock.read_text())
        if lock.get('reader_protocol_sha256') != fingerprint(protocol):
            raise ValueError('Test judge protocol differs from validation')
    source_files.extend([a.summaries, *a.bridge_reports, *a.policy_check_reports])
    scores = aggregate(aliases, [pair[1] for pair in pairs], prepared['arms'])
    manifest = {**prepared, 'reader_protocol': protocol, 'reader_protocol_sha256': fingerprint(protocol),
                'source_hashes': {str(path.resolve()): digest(path) for path in source_files}}
    a.out.mkdir(parents=True, exist_ok=True)
    if (a.out/'complete.json').exists():
        raise ValueError('Preserve completed interpretation artifact')
    write_json(a.out/'scores.json', scores)
    write_json(a.out/'manifest.json', manifest)
    write_json(a.out/'complete.json', {'scores_sha256': digest(a.out/'scores.json'),
                                       'manifest_sha256': fingerprint(manifest), 'rows': len(scores),
                                       'unavailable_arm_rows': sum(row[arm]['missing'] for row in scores for arm in prepared['arms'])})


if __name__ == '__main__':
    main()
