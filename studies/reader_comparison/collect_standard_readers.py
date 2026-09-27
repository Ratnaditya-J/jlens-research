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


def validate_summary_reader(summary_manifest, judge_manifest):
    from hosted_text_reader_lowreference import execution_manifest as flex_manifest
    from hosted_text_reader_standardreference import execution_manifest as standard_manifest
    if judge_manifest != standard_manifest('gpt54standardreference'):
        raise ValueError('This collector requires the separately qualified standard judge')
    if summary_manifest != flex_manifest('gpt54lowreference'):
        raise ValueError('Original registered Flex summarizer execution required')


def execution_source(manifest):
    if 'evidence_encoder_code_sha256' in manifest:
        encoder = Path(__file__).with_name('literal_evidence.py')
        if digest(encoder) != manifest['evidence_encoder_code_sha256']:
            raise ValueError('Evidence encoder differs from recorded execution')
    candidates = [Path(__file__).with_name(name) for name in
                  ('local_text_reader.py', 'local_text_reader_reasoning.py', 'local_text_reader_mistral.py', 'local_text_reader_literal.py', 'local_text_reader_deliberative.py', 'hosted_text_reader.py', 'hosted_text_reader_medium.py', 'hosted_text_reader_escaped.py', 'hosted_text_reader_frontier_pair.py', 'hosted_text_reader_direct.py', 'hosted_text_reader_reference.py', 'hosted_text_reader_lowreference.py', 'hosted_text_reader_standardreference.py')]
    matches = [path for path in candidates if path.exists() and digest(path) == manifest['code_sha256']]
    if len(matches) != 1:
        raise ValueError('Reader execution source is missing or differs from its recorded hash')
    if matches[0].name == 'hosted_text_reader.py':
        from hosted_text_reader import execution_manifest, LOW_COST_CANDIDATES
        if not any(manifest == execution_manifest(candidate) for candidate in LOW_COST_CANDIDATES):
            raise ValueError('Hosted transport, configuration or decoder provenance differs')
    if matches[0].name == 'hosted_text_reader_medium.py':
        from hosted_text_reader_medium import execution_manifest
        if manifest != execution_manifest('gptoss20medium'):
            raise ValueError('Hosted medium transport, configuration or decoder provenance differs')
    if matches[0].name == 'hosted_text_reader_escaped.py':
        from hosted_text_reader_escaped import execution_manifest
        if manifest != execution_manifest('deepseek32escaped'):
            raise ValueError('Hosted escaped-output transport, configuration or decoder provenance differs')
    if matches[0].name == 'hosted_text_reader_frontier_pair.py':
        from hosted_text_reader_frontier_pair import execution_manifest, LOW_COST_CANDIDATES
        if not any(manifest == execution_manifest(candidate) for candidate in LOW_COST_CANDIDATES):
            raise ValueError('Hosted frontier-pair transport, configuration or decoder provenance differs')
    if matches[0].name in ('hosted_text_reader_direct.py', 'hosted_text_reader_reference.py', 'hosted_text_reader_lowreference.py', 'hosted_text_reader_standardreference.py'):
        import importlib
        module = importlib.import_module(matches[0].stem)
        if not any(manifest == module.execution_manifest(candidate) for candidate in module.LOW_COST_CANDIDATES):
            raise ValueError('Hosted single-worker transport, configuration or decoder provenance differs')
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
    p.add_argument('--first-reader-family', choices=['gptoss', 'gpt4'], default='gptoss')
    p.add_argument('--reader-acceptances', type=Path, nargs='*', default=[])
    p.add_argument('--second-reader-family', choices=['qwen', 'mistral', 'deepseek', 'gpt5'], default='qwen')
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
    if any(manifest.get('kind', '').startswith('bounded-hosted-') for manifest, _ in pairs):
        source_files.append(Path(__file__).with_name('budgeted_api_client.py'))
    if any(manifest.get('kind') == 'bounded-hosted-medium20-reader-v1' for manifest, _ in pairs):
        source_files.append(Path(__file__).with_name('budgeted_hosted_medium.py'))
    if any(manifest.get('kind') == 'bounded-hosted-deepseek32escaped-reader-v1' for manifest, _ in pairs):
        source_files.append(Path(__file__).with_name('budgeted_hosted_escaped.py'))
    for kind, transport in [('bounded-hosted-direct-reader-v1','budgeted_hosted_direct.py'), ('bounded-hosted-reference-reader-v1','budgeted_hosted_reference.py'), ('bounded-hosted-lowreference-reader-v1','budgeted_hosted_lowreference.py'), ('bounded-hosted-standardreference-reader-v1','budgeted_hosted_standardreference.py')]:
        if any(m.get('kind') == kind for m,_ in pairs):source_files.append(Path(__file__).with_name(transport))
    if any('evidence_encoder_code_sha256' in manifest for manifest, _ in pairs):
        source_files.append(Path(__file__).with_name('literal_evidence.py'))
    source_files.extend(Path(path) for path in prepared.get('source_hashes', {}))
    if prepared.get('study') == 'archived-gptoss-local-extension-v1':
        source_files.append(Path(__file__).with_name('legacy_local_jobs.py'))
    source_files.extend(reader/'results'/(job['request_id']+'.json')
                        for reader in a.readers for job in jobs
                        if (reader/'results'/(job['request_id']+'.json')).exists())
    guarded = any(m.get('kind') in ('bounded-hosted-direct-reader-v1', 'bounded-hosted-reference-reader-v1', 'bounded-hosted-lowreference-reader-v1', 'bounded-hosted-standardreference-reader-v1') for m,_ in pairs)
    if guarded:
        if len(a.reader_acceptances) != len(pairs):
            raise ValueError('Each new reader needs verified qualification and coverage acceptance')
        from standard_temporal_reviews import load_acceptance
        for path,(manifest,_) in zip(a.reader_acceptances,pairs):
            source_files.extend(Path(source) for source in load_acceptance(path,manifest))
    if prepared['stage'] == 'summaries':
        if len(pairs) != 1:
            raise ValueError('Exactly one registered summarizer required')
        manifest, results = pairs[0]
        if manifest['model']['family'] != a.second_reader_family:
            raise ValueError('Summarizer differs from explicitly selected reader family')
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
    if [m['model']['family'] for m in manifests] != [a.first_reader_family, a.second_reader_family]:
        raise ValueError('Reviewer families differ from explicitly selected protocol')
    reports = [json.loads(path.read_text()) for path in a.bridge_reports]
    for report, manifest in zip(reports, manifests):
        if not report['passed'] or report['manifest_sha256'] != fingerprint(manifest):
            raise ValueError('Reader has not passed the bridge with this exact execution')
    for path, manifest in zip(a.policy_check_reports, manifests):
        report = json.loads(path.read_text())
        if not report['passed'] or report['manifest_sha256'] != fingerprint(manifest):
            raise ValueError('Reader has not passed the predefined policy check with this execution')
    summary = json.loads(a.summaries.read_text())
    validate_summary_reader(summary['summarizer_manifest'], manifests[1])
    protocol = {'kind': ('local-two-reader-mistral-v1' if a.second_reader_family == 'mistral' else 'local-two-reader-v1'), 'readers': manifests,
                'bridge_report_sha256': [digest(path) for path in a.bridge_reports],
                'policy_check_report_sha256': [digest(path) for path in a.policy_check_reports],
                'summarizer_manifest': summary['summarizer_manifest'],
                'collector_code_sha256': digest(__file__),
                'rule': 'Minimum of two valid ordinal scores; unavailable otherwise. Both individual scores retained.',
                'dependency': ('GPT-OSS first judge shares the archived subject base family; Qwen provides the summarizer and second judge. Original premium judgments remain separate.' if prepared.get('study') == 'archived-gptoss-local-extension-v1' else 'Qwen summarizer and second judge share a base family with the Oracle verbalizer; GPT-OSS is the independent-family judge.')}
    if a.second_reader_family == 'mistral':
        protocol['dependency'] = ('GPT-OSS first judge shares the archived subject base family; Mistral supplies both summaries and the second judge. Original premium judgments remain separate.' if prepared.get('study') == 'archived-gptoss-local-extension-v1' else 'Both text-judge families differ from the Qwen subject and Oracle verbalizer. Mistral supplies summaries and the second judge, so self-evaluation dependence remains.')
    if a.second_reader_family == 'deepseek':
        if not all(m.get('kind', '').startswith('bounded-hosted-') for m in manifests):
            raise ValueError('The DeepSeek protocol requires two registered hosted executions')
        protocol['kind'] = 'hosted-two-reader-deepseek-v1'
        protocol['dependency'] = ('GPT-OSS first judge shares the archived subject base family; DeepSeek supplies summaries and the second judge. Original premium judgments remain separate.' if prepared.get('study') == 'archived-gptoss-local-extension-v1' else 'Both text-judge families differ from the Qwen subject and Oracle verbalizer. DeepSeek supplies summaries and the second judge, so self-evaluation dependence remains.')
        protocol['hosting_limit'] = 'Provider and request settings are pinned and raw replies retained; hosted weight files cannot be hash-pinned. Results describe these recorded executions.'
    if a.first_reader_family == 'gpt4':
        from hosted_text_reader_reference import execution_manifest as reference_manifest
        from hosted_text_reader_direct import execution_manifest as direct_manifest
        from hosted_text_reader_lowreference import execution_manifest as lowreference_manifest
        from hosted_text_reader_standardreference import execution_manifest as standard_manifest
        if not guarded:raise ValueError('New reference protocols require verified acceptance')
        if manifests == [reference_manifest('gpt41reference'), direct_manifest('deepseek32direct')]:
            protocol['kind'] = 'hosted-gpt41-deepseek-direct-v1'
            protocol['dependency'] = 'GPT-4.1 contributed bridge reference labels; bridge agreement is compatibility, not independent accuracy. DeepSeek supplies summaries and the second judge, so self-evaluation dependence remains.'
        elif manifests == [reference_manifest('gpt41reference'), lowreference_manifest('gpt54lowreference')]:
            protocol['kind'] = 'hosted-reference-pair-v1'
            protocol['dependency'] = 'Both judges contributed bridge reference labels and share OpenAI provenance. Agreement is compatibility, not independent confirmation. GPT-5.4 supplies summaries and the second judgment; self-evaluation dependence remains. Per-reader results must be reported separately.'
        elif manifests == [reference_manifest('gpt41reference'), standard_manifest('gpt54standardreference')]:
            protocol['kind'] = 'hosted-reference-standard-judge-flex-summary-v1'
            protocol['dependency'] = 'GPT4 and GPT5 share vendor and bridge-reference provenance. GPT5 Flex summaries are fixed; the GPT5 standard-route judge is separately qualified. All second-judge scores in this protocol use standard routing. No Flex score substitution. Self-evaluation dependence and hosted-weight uncertainty remain; this protocol is distinct from original Flex-judge results.'
        else:raise ValueError('Unregistered reference-model pair')
        protocol['acceptance_sha256'] = [digest(path) for path in a.reader_acceptances]
        protocol['hosting_limit'] = 'Hosted weights cannot be hash-pinned; the exact recorded execution defines scope. Original premium results remain separate.'
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
