import sys
from pathlib import Path
from copy import deepcopy
import unittest
sys.path.insert(0, str(Path(__file__).parents[1]/'scripts'))
import amber_fusion as fusion
import amber_monitor as base


def rows():
    result = []
    for group in range(6):
        for label in (False, True):
            result.append({'episode_id': f'{group}-{int(label)}', 'template_id': f't{group}',
                'pair_id': f'p{group}', 'split': 'train', 'label': label,
                'values': {'output': {'prompt': f'groupword{group}',
                    'final_answer': 'forbidden update' if label else 'allowed result', 'action_trace': []},
                    'activation': [float(label), float(group), 1.]}})
    return result


class FusionTests(unittest.TestCase):
    def test_no_template_or_pair_overlap_and_fold_artifacts_replay(self):
        data = rows(); fitted = fusion.fit(data, ['output', 'activation'], 3, 17)
        indexed = {r['episode_id']: r for r in data}
        for fold in fitted['folds']:
            held = [indexed[k] for k in fold['held_episode_ids']]
            for arm, ids in fold['training_episode_ids'].items():
                train = [indexed[k] for k in ids]
                self.assertFalse({r['template_id'] for r in held} & {r['template_id'] for r in train})
                self.assertFalse({r['pair_id'] for r in held} & {r['pair_id'] for r in train})
                replay = base.predict(fold['component_fits'][arm]['artifact'], [r['values'][arm] for r in held])
                recorded = {r['episode_id']: r['scores'][fitted['artifact']['arms'].index(arm)] for r in fitted['out_of_fold_scores']}
                self.assertEqual(replay, [recorded[r['episode_id']] for r in held])
        self.assertLess(fitted['native_margin_max_difference'], 1e-8)
        for arm, final in fitted['component_fits'].items():
            self.assertEqual(final, base.fit('activation' if arm == 'activation' else 'text', arm, fusion.component_rows(data, arm)))

    def test_held_group_labels_cannot_affect_its_component_fit(self):
        data = rows(); first = fusion.fit(data, ['output', 'activation'], 3, 17)
        changed = deepcopy(data); changed[0]['label'] = not changed[0]['label']
        second = fusion.fit(changed, ['output', 'activation'], 3, 17)
        assignment = first['training_manifest']['fold_assignment']
        self.assertEqual(assignment, second['training_manifest']['fold_assignment'])
        fold = next(r['fold'] for r in assignment if r['episode_id'] == data[0]['episode_id'])
        self.assertEqual(first['folds'][fold]['component_fits'], second['folds'][fold]['component_fits'])

    def test_transitive_pair_connections_keep_templates_together(self):
        data = rows(); data[2]['pair_id'] = data[0]['pair_id']; data[4]['pair_id'] = data[3]['pair_id']
        assignments = fusion.fold_assignment(data, 3, 17)
        connected = [r for r in assignments if r['episode_id'].split('-')[0] in ('0','1','2')]
        self.assertEqual(len({r['fold'] for r in connected}), 1)
        self.assertEqual(len({r['group'] for r in connected}), 1)

    def test_unknown_and_missing_rows_retained_and_not_imputed(self):
        data = rows(); data[0]['label'] = None; data[2]['values']['activation'] = None
        result = fusion.fit(data, ['output', 'activation'], 3, 17)
        self.assertEqual(result['artifact']['training_count'], 10)
        self.assertEqual(len(result['training_manifest']['fold_assignment']), 12)
        self.assertEqual(result['training_manifest']['exclusions'], [
            {'episode_id': '0-0', 'unknown_label': True, 'missing_arms': []},
            {'episode_id': '1-0', 'unknown_label': False, 'missing_arms': ['activation']}])
        self.assertEqual(result['component_fits']['output']['artifact']['training_count'], 11)
        self.assertEqual(result['component_fits']['activation']['artifact']['training_count'], 10)

    def test_rejects_nontraining_metadata_leak_and_invalid_folds(self):
        for split in ('calibration','baseline','heldout_template','adaptation'):
            data = rows(); data[0]['split'] = split
            with self.assertRaises(ValueError): fusion.fit(data, ['output', 'activation'], 3, 17)
        data = rows(); data[0]['values']['output']['oracle'] = True
        with self.assertRaises(ValueError): fusion.fit(data, ['output', 'activation'], 3, 17)
        with self.assertRaises(ValueError): fusion.fit(rows(), ['output', 'activation'], 7, 17)
        data = rows()
        for row in data: row['template_id'] = 'same'
        with self.assertRaises(ValueError): fusion.fit(data, ['output', 'activation'], 2, 17)

    def test_one_class_fold_fails_without_seed_retry(self):
        data = rows()[:4]
        for row in data: row['label'] = row['template_id'] == 't0'
        with self.assertRaisesRegex(ValueError, 'both classes'): fusion.fit(data, ['output', 'activation'], 2, 17)


if __name__ == '__main__': unittest.main()
