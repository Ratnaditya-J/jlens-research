"""Predeclared individual-judge sensitivity analyses; no additional inference."""
from contracts import conservative_threshold
from metrics import operating_point


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
            rows[arm] = {'threshold': threshold, 'validation_benign_n': len(values),
                         'validation_false_positives': sum(value >= threshold for value in values)}
        if model in result:
            raise ValueError('Individual reader names must be unique')
        result[model] = rows
    return result


def evaluate_individuals(episodes, scores, calibration):
    report = {}
    for index, (model, arms) in enumerate(calibration.items()):
        metrics = {}
        for arm, operating in arms.items():
            pairs = [(episode['label'], individual_score(scores.get(episode['episode_id'], {}), arm, index))
                     for episode in episodes]
            usable = [(label, value) for label, value in pairs if value is not None]
            metrics[arm] = operating_point([label for label, _ in usable], [value for _, value in usable], operating['threshold'])
            metrics[arm].update(requested=len(pairs), unavailable=len(pairs)-len(usable))
        report[model] = metrics
    return report
