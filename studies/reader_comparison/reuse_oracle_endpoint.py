"""Reuse identical saved activation readouts across endpoints, without new RNG draws."""
import argparse
import json
from pathlib import Path
from contracts import fingerprint
from smoke import digest, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--captures', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--endpoint', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    cm = json.loads((a.captures/'manifest.json').read_text())
    sm = json.loads((a.source/'manifest.json').read_text())
    if sm['capture_manifest_sha256'] != fingerprint(cm) or sm['subject_identity'] != cm['identity']:
        raise ValueError('Source reader belongs to different captures')
    cells = {}
    targets = {}
    for path in sorted(a.captures.glob('*/complete.json')):
        done = json.loads(path.read_text())
        if done['manifest_sha256'] != fingerprint(cm) or digest(path.parent/'cells.json') != done['cells_sha256']:
            raise ValueError('Capture metadata changed')
        for cell in json.loads((path.parent/'cells.json').read_text()):
            cells[cell['cell_id']] = cell
            if cell['endpoint'] == a.endpoint:
                targets.setdefault((cell['layer'], cell['state_sha256']), []).append(cell['cell_id'])
    if not targets:
        raise ValueError('No requested endpoint cells')
    source = {}
    source_hashes = {}
    for path in sorted(a.source.glob('batch-*.json')):
        batch = json.loads(path.read_text())
        if batch['request']['manifest_sha256'] != fingerprint(sm) or batch['request_sha256'] != fingerprint(batch['request']):
            raise ValueError('Source Oracle batch provenance changed')
        source_hashes[path.name] = digest(path)
        for result in batch['results']:
            cell = cells[result['cell_id']]
            if cell['state_sha256'] != result['state_sha256'] or cell['endpoint'] != sm['endpoint']:
                raise ValueError('Source result activation mismatch')
            key = (cell['layer'], cell['state_sha256'])
            if key in source:
                raise ValueError('Multiple source draws for an identical activation')
            source[key] = result
    if set(targets) - set(source):
        raise ValueError('Some target activations lack an identical source readout')
    manifest = {**sm, 'endpoint': a.endpoint,
                'ordered_cell_ids': [ids[0] for ids in targets.values()],
                'identical_state_aliases': {ids[0]: ids for ids in targets.values()},
                'reuse': {'source_manifest_sha256': fingerprint(sm), 'source_endpoint': sm['endpoint'],
                          'source_batch_sha256': source_hashes, 'code_sha256': digest(__file__),
                          'rule': 'Same checkpoint, capture manifest, layer, and saved activation SHA256; preserve the exact original text and generated IDs.'}}
    results = []
    for key, aliases in targets.items():
        original = source[key]
        results.append({**original, 'cell_id': aliases[0], 'alias_cell_ids': aliases,
                        'reused_source_cell_id': original['cell_id']})
    if a.out.exists():
        raise ValueError('Preserve existing endpoint output')
    a.out.mkdir(parents=True)
    write_json(a.out/'manifest.json', manifest)
    request = {'manifest_sha256': fingerprint(manifest), 'cell_ids': manifest['ordered_cell_ids'],
               'kind': 'exact-activation-reuse'}
    write_json(a.out/'batch-000000.json', {'request': request, 'request_sha256': fingerprint(request), 'results': results})
    write_json(a.out/'complete.json', {'manifest_sha256': fingerprint(manifest), 'unique_states': len(results),
                                      'aliased_cells': sum(len(ids) for ids in targets.values()), 'new_inference_calls': 0})
    print(json.dumps({'unique_states': len(results), 'aliased_cells': sum(len(ids) for ids in targets.values())}))


if __name__ == '__main__':
    main()
