"""CPU-only contracts: provenance, causal positions, splits and paired coverage."""
import hashlib
import json
import math


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def parse_json_reply(text):
    text=text.strip()
    if text.startswith('```json\n') and text.endswith('\n```'):
        text=text[len('```json\n'):-len('\n```')]
    result=json.loads(text)
    if not isinstance(result,dict):raise ValueError('Expected one JSON object')
    return result


def validate_cell(cell, identity, supported_layers):
    required = {'episode_id','family_id','split','identity_sha256','prefix_ids','position','layer','state_sha256'}
    if required - cell.keys():
        raise ValueError(f'Missing fields: {sorted(required-cell.keys())}')
    if cell['identity_sha256'] != fingerprint(identity):
        raise ValueError('Checkpoint / precision / adapter identity mismatch')
    if cell['layer'] not in supported_layers:
        raise ValueError('Unsupported reader layer')
    if not cell['prefix_ids'] or cell['position'] != len(cell['prefix_ids'])-1:
        raise ValueError('Saved causal prefix must end exactly at read position')
    if cell['split'] not in {'train','validation','test','control'}:
        raise ValueError('Unknown split')
    return fingerprint(cell)


def check_splits(episodes):
    seen_ids, families = set(), {}
    for row in episodes:
        if row['episode_id'] in seen_ids:
            raise ValueError('Duplicate episode')
        seen_ids.add(row['episode_id'])
        group = row['family_id']
        split = row['split']
        if group in families and families[group] != split:
            raise ValueError('Scenario-family leakage across splits')
        families[group] = split
    return families


def validate_cached_result(result, request):
    # Includes precise model, prompt, payload, sampling and state hashes.
    if result.get('request_sha256') != fingerprint(request):
        raise ValueError('Stale or foreign result cache')
    if result.get('requested_model') != request['model']:
        raise ValueError('Wrong per-request reviewer model')
    if result.get('status') != 'ok':
        raise ValueError('Failed result cannot be scored as a negative')


def paired_rows(reference_ids, arm_results):
    wanted = set(reference_ids)
    if len(reference_ids) != len(wanted):
        raise ValueError('Duplicate reference cells')
    available = {}
    for arm, rows in arm_results.items():
        by_id = {}
        for row in rows:
            key = row['cell_id']
            if key in by_id or key not in wanted:
                raise ValueError('Duplicate or foreign result cell')
            by_id[key] = row
        available[arm] = by_id
    common = {i for i in wanted if all(a.get(i,{}).get('status') == 'ok' for a in available.values())}
    coverage = {arm: {'requested':len(wanted),'ok':sum(r.get('status')=='ok' for r in rows.values()),'missing':len(wanted-rows.keys())} for arm,rows in available.items()}
    return sorted(common), coverage


def conservative_threshold(benign_scores, target_fpr=0.05):
    values = sorted(map(float,benign_scores),reverse=True)
    if not values or not all(math.isfinite(v) for v in values):
        raise ValueError('Finite benign validation scores required')
    if not 0 <= target_fpr < 1:
        raise ValueError('Invalid target FPR')
    return math.nextafter(values[math.floor(target_fpr*len(values))], math.inf)


def strictly_before(offsets, character_boundary):
    """Last token wholly before an action; a token crossing the boundary is excluded."""
    candidates = [i for i,(start,end) in enumerate(offsets) if 0 <= start < end <= character_boundary]
    if not candidates:
        raise ValueError('No wholly preceding token')
    return candidates[-1]
