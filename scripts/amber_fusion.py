"""Grouped out-of-fold stacking over the native frozen AMBER monitor fits.

Template and matched-pair connectivity define indivisible folds. No calibration,
evaluation, or caller-supplied in-sample scores may enter the stack's training.
"""
import json
import math
import sys
import warnings
import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import amber_monitor as base

VERSION = 'amber-grouped-fusion-provider-v1'
ARMS = {'output', 'raw_cot', 'context', 'activation'}


def fold_assignment(rows, fold_count, seed):
    if type(fold_count) is not int or fold_count < 2 or type(seed) is not int:
        raise ValueError('at least two prespecified folds and an integer seed required')
    parent = {}
    def root(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]; key = parent[key]
        return key
    for row in rows:
        keys = [('template', row['template_id']), ('pair', row['pair_id'])]
        a, b = [root(key) for key in keys]
        parent[max(a, b)] = min(a, b)
    members = {}
    for key in parent:
        members.setdefault(root(key), []).append(key)
    groups = {key: base.digest(sorted(value)) for key, value in members.items()}
    ordered = sorted(groups.values(), key=lambda g: (base.digest({'group': g, 'seed': seed}), g))
    if len(ordered) < fold_count:
        raise ValueError('too few independent connected template/pair groups for requested folds')
    group_fold = {group: i % fold_count for i, group in enumerate(ordered)}
    return [{'episode_id': row['episode_id'], 'group': groups[root(('template', row['template_id']))],
             'fold': group_fold[groups[root(('template', row['template_id']))]]} for row in rows]


def validate_rows(rows, arms):
    if not isinstance(arms, list) or len(arms) < 2 or len(set(arms)) != len(arms) or not set(arms) <= ARMS:
        raise ValueError('at least two distinct supported component arms required')
    if not rows or len({r['episode_id'] for r in rows}) != len(rows):
        raise ValueError('empty or duplicate fusion training observations')
    for row in rows:
        if set(row) != {'episode_id', 'template_id', 'pair_id', 'split', 'label', 'values'}:
            raise ValueError('unknown training row fields')
        if row['split'] != 'train':
            raise ValueError('only training rows may enter fusion fitting')
        if any(not isinstance(row[k], str) or not row[k].strip() for k in ('episode_id', 'template_id', 'pair_id')):
            raise ValueError('nonempty episode/template/pair identities required')
        if row['label'] is not None and type(row['label']) is not bool:
            raise ValueError('label must be bool or explicit unknown')
        if not isinstance(row['values'], dict) or set(row['values']) != set(arms):
            raise ValueError('every component requires a value or explicit missing value')
        for arm, value in row['values'].items():
            if value is None: continue
            if arm == 'activation':
                if not isinstance(value, list) or not value or any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
                    raise ValueError('finite activation vector required')
            else: base.text(value, arm)


def component_rows(rows, arm):
    return [{'episode_id': r['episode_id'], 'split': r['split'], 'label': r['label'], 'value': r['values'][arm]}
            for r in rows if r['label'] is not None and r['values'][arm] is not None]


def fit(rows, arms, fold_count, seed):
    validate_rows(rows, arms)
    assignments = fold_assignment(rows, fold_count, seed)
    by_id = {r['episode_id']: r for r in assignments}
    eligible = [r for r in rows if r['label'] is not None and all(r['values'][a] is not None for a in arms)]
    if len({r['label'] for r in eligible}) != 2:
        raise ValueError('fusion requires both classes among complete training cases')
    exclusions = [{'episode_id': r['episode_id'], 'unknown_label': r['label'] is None,
                   'missing_arms': [a for a in arms if r['values'][a] is None]}
                  for r in rows if r['label'] is None or any(r['values'][a] is None for a in arms)]
    oof = {r['episode_id']: {} for r in eligible}; folds = []
    for index in range(fold_count):
        training = [r for r in rows if by_id[r['episode_id']]['fold'] != index]
        held = [r for r in eligible if by_id[r['episode_id']]['fold'] == index]
        # Fit every prespecified component/fold even if its held slice has no
        # complete examples. Never retry a new seed to hide a one-class fold.
        fits = {}; train_ids = {}
        for arm in arms:
            selected = component_rows(training, arm)
            fitted = base.fit('activation' if arm == 'activation' else 'text', arm, selected)
            fits[arm] = fitted
            train_ids[arm] = [r['episode_id'] for r in selected]
            values = base.predict(fitted['artifact'], [r['values'][arm] for r in held]) if held else []
            for row, value in zip(held, values, strict=True): oof[row['episode_id']][arm] = value
        folds.append({'fold': index, 'training_episode_ids': train_ids,
                      'held_episode_ids': [r['episode_id'] for r in held], 'component_fits': fits})
    score_rows = [{'episode_id': r['episode_id'], 'fold': by_id[r['episode_id']]['fold'],
                   'group': by_id[r['episode_id']]['group'], 'label': r['label'],
                   'scores': [oof[r['episode_id']][a] for a in arms]} for r in eligible]
    raw = np.asarray([r['scores'] for r in score_rows], dtype=np.float64)
    if raw.shape != (len(eligible), len(arms)) or not np.isfinite(raw).all():
        raise ValueError('incomplete/nonfinite out-of-fold matrix')
    scaler = StandardScaler(); matrix = scaler.fit_transform(raw)
    settings = {'C': 1.0, 'max_iter': 3000, 'solver': 'lbfgs', 'random_state': seed}
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        classifier = LogisticRegression(**settings).fit(matrix, [r['label'] for r in eligible])
    weights = classifier.coef_[0] / scaler.scale_
    intercept = float(classifier.intercept_[0] - np.dot(weights, scaler.mean_))
    reference = classifier.decision_function(matrix)
    max_difference = float(np.max(np.abs(raw @ weights + intercept - reference)))
    if max_difference >= 1e-8: raise ValueError('fusion portable margin replay failed')
    final = {arm: base.fit('activation' if arm == 'activation' else 'text', arm, component_rows(rows, arm)) for arm in arms}
    training_manifest = {'version': VERSION, 'rows_sha256': base.digest(rows), 'arms': arms,
        'fold_count': fold_count, 'seed': seed, 'fold_assignment': assignments,
        'grouping': 'connected-template-and-pair; label-blind hash order, round-robin folds',
        'exclusions': exclusions, 'out_of_fold_scores_sha256': base.digest(score_rows),
        'folds_sha256': base.digest(folds), 'base_fit_sha256': {a: base.digest(v) for a, v in final.items()},
        'fit_settings': settings, 'sklearn_version': sklearn.__version__}
    artifact = {'version': VERSION, 'kind': 'fusion', 'arm': 'fused', 'arms': arms,
        'weights': weights.tolist(), 'intercept': intercept, 'training_count': len(eligible),
        'positive_count': sum(r['label'] for r in eligible), 'sklearn_version': sklearn.__version__,
        'training_manifest_sha256': base.digest(training_manifest),
        'claim_license': 'grouped_crossfit_training_only_no_efficacy_claim'}
    return {'artifact': artifact, 'artifact_sha256': base.digest(artifact), 'training_manifest': training_manifest,
            'component_fits': final, 'folds': folds, 'out_of_fold_scores': score_rows,
            'native_margin_max_difference': max_difference,
            'limitations': ['out-of-fold scores train the stack and are not a held-out evaluation of the stack',
                'complete-case meta-fitting excludes explicit missing rows; deployment abstains when any component is missing',
                'final component fits use all eligible training rows; fusion thresholds require separate benign calibration',
                'group assignments do not establish template independence, statistical power or research efficacy']}


if __name__ == '__main__':
    request = json.load(sys.stdin)
    if request.get('operation') != 'fit': raise ValueError('unknown fusion operation')
    print(json.dumps(fit(request['rows'], request['arms'], request['fold_count'], request['seed']), allow_nan=False, sort_keys=True))
