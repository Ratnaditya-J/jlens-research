"""Audit action-value visibility in held-out causal prefixes; descriptive, no fitting."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from contracts import fingerprint
from smoke import digest, write_json

FULL = re.compile(r'<action>\s*\{\s*"[^"\n]+"\s*:\s*(true|false)\b')
PARTIAL = re.compile(r'<action>\s*\{\s*"[^"\n]+"\s*:\s*(t|tr|tru|f|fa|fal|fals)$')


def visibility(generated_prefix):
    if FULL.search(generated_prefix):
        return 'complete_boolean_visible'
    if PARTIAL.search(generated_prefix.rstrip()):
        return 'unambiguous_partial_boolean_visible'
    return 'boolean_not_yet_explicit'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--features', type=Path, required=True)
    p.add_argument('--captures', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    manifest = json.loads(a.features.read_text())
    cm = json.loads((a.captures/'manifest.json').read_text())
    if fingerprint(cm) != manifest['capture_manifest_sha256']:
        raise ValueError('Capture manifest mismatch')
    ids = sorted({r['episode_id'] for r in manifest['rows'] if r['split'] in ['test']})
    if len(ids) != 128:
        raise ValueError('Expected all128 held-out episodes')
    sources = {str(a.features): digest(a.features), str(a.captures/'manifest.json'): digest(a.captures/'manifest.json')}
    records = []
    endpoints = ['end_prompt', 'before_action', 'before_action_32', 'before_action_64', 'during_action', 'after_action']
    for eid in ids:
        cp = a.captures/eid/'cells.json'
        done = json.loads(cp.with_name('complete.json').read_text())
        if digest(cp) != done['cells_sha256'] or done['manifest_sha256'] != fingerprint(cm):
            raise ValueError('Cell provenance mismatch')
        sources[str(cp)] = digest(cp)
        cells = json.loads(cp.read_text())
        by_endpoint = {}
        for e in endpoints:
            group = [x for x in cells if x['endpoint'] == e]
            if len(group) != 4 or len({(x['prefix_text'], x['position']) for x in group}) != 1:
                raise ValueError('Missing endpoint or differing per-layer prefixes')
            by_endpoint[e] = group[0]
        baseline = by_endpoint['end_prompt']
        if baseline['split'] not in ['test']:
            raise ValueError('Only held-out prefixes allowed')
        for e, cell in by_endpoint.items():
            n = len(cell['prefix_ids']) - len(baseline['prefix_ids'])
            text = cell['prefix_text']
            if n > 0:
                if not text.startswith(baseline['prefix_text']):
                    raise ValueError('Unexpected prefix decoding boundary')
                generated = text[len(baseline['prefix_text']):]
            else:
                generated = ''
            records.append({'episode_id': eid, 'split': cell['split'], 'endpoint': e,
                            'generated_tokens_visible': max(0, n), 'visibility': visibility(generated)})
    panels = {}
    for split in ['test']:
        panels[split] = {}
        for e in endpoints:
            rows = [r for r in records if r['split'] == split and r['endpoint'] == e]
            counts = Counter(r['visibility'] for r in rows)
            panels[split][e] = {'n': len(rows), 'visibility_counts': dict(counts),
                               'generated_tokens_min': min(r['generated_tokens_visible'] for r in rows),
                               'generated_tokens_max': max(r['generated_tokens_visible'] for r in rows)}
    write_json(a.out, {'panels': panels, 'rows': records, 'source_hashes': sources,
                      'code_sha256': digest(__file__),
                      'scope': 'Descriptive lexical visibility in held-out prefixes, after primary results were already inspected. Complete boolean or a unique prefix of true/false is visible choice evidence; absence does not imply no other textual cues. No detector fitting, threshold calibration, performance scoring or causal inference.'})
    print(json.dumps(panels))


if __name__ == '__main__':
    main()
