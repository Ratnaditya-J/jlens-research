from pathlib import Path
import json
from contracts import fingerprint
from smoke import digest
from validate_reader_gates import ready
from evaluate_local_bridge import evaluate


def execution_source(manifest):
    from hosted_text_reader_standardreference import execution_manifest
    if manifest != execution_manifest('gpt54standardreference'):
        raise ValueError('Standard-route execution source/settings changed')
    return Path(__file__).with_name('hosted_text_reader_standardreference.py')

def verify_qualification(reader, gates, bridge, policy, expected):
    manifest = json.loads((reader/'manifest.json').read_text())
    if manifest != expected:
        raise ValueError('Qualification execution differs from proposed coverage execution')
    execution_source(manifest)
    complete = json.loads((gates/'complete.json').read_text())
    if not complete['passed'] or complete['reader_manifest_sha256'] != digest(reader/'manifest.json'):
        raise ValueError('Both fixed qualification gates must pass')
    sources = [reader/'manifest.json', gates/'complete.json']
    for name, fixtures, completion in [('bridge', bridge, 'local-bridge-jobs-complete.json'),
                                      ('policy', policy, 'local-policy-check-jobs-complete.json')]:
        if not ready(reader, fixtures, completion):
            raise ValueError('Qualification outputs are incomplete')
        protocol = json.loads((fixtures/'protocol.json').read_text())
        for artifact in ['jobs', 'references']:
            if digest(fixtures/(artifact+'.json')) != protocol[artifact+'_sha256']:
                raise ValueError('Qualification fixture changed')
        path = gates/(name+'.json')
        report = json.loads(path.read_text())
        if (digest(path) != complete['reports_sha256'][name] or not report['passed']
                or report['manifest_sha256'] != fingerprint(manifest)
                or report['protocol_sha256'] != digest(fixtures/'protocol.json')):
            raise ValueError('Qualification report provenance differs')
        references = json.loads((fixtures/'references.json').read_text())['references']
        results = {ref['request_id']: json.loads((reader/'results'/(ref['request_id']+'.json')).read_text())
                   for ref in references}
        actual = evaluate(references, results, fingerprint(manifest))
        if (actual['valid_fraction'] < protocol['valid_json_fraction_min'] or
                actual['exact_agreement_fraction'] < protocol['exact_reference_agreement_fraction_min']):
            raise ValueError('Raw qualification judgments fail the fixed gate')
        for score, minimum in protocol.get('minimum_score_recall', {}).items():
            subset = [row for row in actual['rows'] if row['reference_score'] == int(score)]
            if not subset or sum(row['exact_agreement'] for row in subset)/len(subset) < minimum:
                raise ValueError('Raw qualification judgments fail a class gate')
        sources.extend([fixtures/'protocol.json', fixtures/'jobs.json', fixtures/'references.json', path, reader/completion])
        sources.extend(reader/'results'/(ref['request_id']+'.json') for ref in references)
    return {str(path.resolve()): digest(path) for path in sources}

