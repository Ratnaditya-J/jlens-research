"""Outcome-blind audit of temporal endpoints and duplicate representations."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from contracts import fingerprint
from smoke import digest, write_json


def audit(captures):
    manifest = json.loads((captures/'manifest.json').read_text())
    endpoints = defaultdict(lambda: {'episodes': set(), 'cells': 0, 'generated_positions': 0,
                                    'prompt_positions': 0, 'unique_states': set(), 'unique_prefixes': set()})
    paired, identical = 0, 0
    failures = []
    for path in sorted(captures.glob('*/complete.json')):
        done = json.loads(path.read_text())
        cellpath = path.parent/'cells.json'
        if done['manifest_sha256'] != fingerprint(manifest) or done['cells_sha256'] != digest(cellpath):
            raise ValueError('Capture metadata provenance changed')
        cells = json.loads(cellpath.read_text())
        by_key = {}
        for cell in cells:
            key = (cell['endpoint'], cell['layer'])
            if key in by_key:
                raise ValueError('Duplicate layer endpoint')
            by_key[key] = cell
            if cell['position'] != len(cell['prefix_ids']) - 1:
                raise ValueError('Noncausal capture position')
            entry = endpoints[cell['endpoint']]
            entry['episodes'].add(cell['episode_id'])
            entry['cells'] += 1
            entry['generated_positions' if cell['position_in_generated_output'] else 'prompt_positions'] += 1
            entry['unique_states'].add((cell['layer'], cell['state_sha256']))
            entry['unique_prefixes'].add(fingerprint(cell['prefix_ids']))
        for layer in manifest['layers']:
            first = by_key.get(('end_prompt', layer))
            second = by_key.get(('before_action', layer))
            if first is None or second is None:
                failures.append({'episode_id': path.parent.name, 'layer': layer, 'reason': 'Missing paired endpoint'})
                continue
            paired += 1
            same = all(first[k] == second[k] for k in ('prefix_ids', 'position', 'state_sha256', 'position_in_generated_output'))
            identical += same
            if not same:
                failures.append({'episode_id': path.parent.name, 'layer': layer, 'reason': 'Endpoint representations differ'})
    return {'capture_manifest_sha256': fingerprint(manifest),
            'endpoints': {name: {key: len(value) if isinstance(value, set) else value
                                  for key, value in row.items()} for name, row in sorted(endpoints.items())},
            'end_prompt_vs_before_action': {'paired_cells': paired, 'identical_cells': identical,
                                           'all_equivalent': paired > 0 and paired == identical and not failures,
                                           'exceptions': failures},
            'scope': 'Metadata-verified causal locations and saved state hashes; no behavioral labels or test performance inspected. Earlier offsets inside the prompt are not earlier stages of generated deliberation.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--captures', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = audit(a.captures)
    write_json(a.out, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
