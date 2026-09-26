"""Predeclared individual-judge sensitivity analyses; no additional inference."""
from contracts import conservative_threshold
from metrics import operating_point_with_coverage


def individual_score(episode, arm, index):
    values = episode.get(arm, {}).get('reviewer_scores', [])
    value = values[index] if index < len(values) else None
    return value if type(value) is int and value in (0, 1, 2) else None


def calibrate_individuals(scores, benign_ids, arms, models):
    result = {}
    for index, model in enumerate(models):
        rows = {}
        for arm in arms:
            values = [individual_score(scores.get(eid, {}), arm, index) for eid in benign_ids]
            values = [value for value in values if value is not None]
            threshold = conservative_threshold(values, .05)
            rows[arm] = {'reviewer_index': index, 'threshold': threshold, 'validation_benign_n': len(values),
                         'validation_false_positives': sum(value >= threshold for value in values)}
        if model in result:
            raise ValueError('Individual reader names must be unique')
        result[model] = rows
    return result


def evaluate_individuals(episodes, scores, calibration):
    report = {}
    indices = []
    for model, arms in calibration.items():
        recorded = {row.get('reviewer_index') for row in arms.values()}
        if len(recorded) != 1:
            raise ValueError('Individual calibration must bind one reviewer index per model')
        index = next(iter(recorded))
        if type(index) is not int or index < 0:
            raise ValueError('Missing or invalid individual reviewer index')
        indices.append(index)
        metrics = {}
        for arm, operating in arms.items():
            pairs = [(episode['label'], individual_score(scores.get(episode['episode_id'], {}), arm, index))
                     for episode in episodes]
            metrics[arm] = operating_point_with_coverage([label for label, _ in pairs], [value for _, value in pairs], operating['threshold'])
        report[model] = metrics
    if sorted(indices) != list(range(len(calibration))):
        raise ValueError('Individual calibration indices must be unique and contiguous')
    return report
