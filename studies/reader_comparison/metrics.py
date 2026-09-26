"""Paired detection metrics with family-cluster bootstrap and explicit coverage."""
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score


def operating_point(y, scores, threshold):
    y=np.asarray(y);scores=np.asarray(scores,dtype=float)
    if y.shape!=scores.shape or not np.isfinite(scores).all():raise ValueError('Invalid paired scores')
    if not set(y.tolist())<={0,1}:raise ValueError('Unknown outcomes must be excluded explicitly')
    flagged=scores>=threshold;positive=y==1;benign=y==0
    tp=int(np.sum(flagged&positive));fp=int(np.sum(flagged&benign))
    npos=int(positive.sum());nben=int(benign.sum())
    return {'n':len(y),'positive':npos,'benign':nben,'tp':tp,'fp':fp,'fn':npos-tp,'tn':nben-fp,'tpr':tp/npos if npos else None,'fpr':fp/nben if nben else None,'auroc':float(roc_auc_score(y,scores)) if npos and nben else None,'auprc':float(average_precision_score(y,scores)) if npos and nben else None,'prevalence':npos/len(y) if len(y) else None}


def operating_point_with_coverage(y, scores, threshold):
    if len(y) != len(scores) or not set(y) <= {0, 1}:
        raise ValueError('Coverage requires paired known outcomes')
    valid = [(label, score) for label, score in zip(y, scores) if score is not None]
    result = operating_point([label for label, _ in valid], [score for _, score in valid], threshold)
    result.update(requested=len(y), unavailable=len(y)-len(valid))
    for label, name, count in [(1, 'tpr', 'tp'), (0, 'fpr', 'fp')]:
        total = sum(value == label for value in y)
        missing = sum(value == label and score is None for value, score in zip(y, scores))
        result['missing_'+('positive' if label else 'benign')+'_n'] = missing
        result['missingness_'+name+'_bounds'] = [result[count]/total, (result[count]+missing)/total] if total else None
    return result


def operating_point_with_cluster_uncertainty(y, scores, groups, threshold, replicates=2000, seed=20260926):
    """Conditional-on-availability rates; missingness bounds remain separate.

    Resample whole families, preserving all seeds and missing responses. Count
    aggregation is equivalent to concatenating every selected family's rows.
    """
    result = operating_point_with_coverage(y, scores, threshold)
    if len(groups) != len(y) or type(replicates) is not int or replicates < 1:
        raise ValueError('Invalid cluster bootstrap inputs')
    unique = sorted(set(groups))
    counts = np.zeros((len(unique), 4), dtype=np.int64)
    positions = {group: index for index, group in enumerate(unique)}
    for label, score, group in zip(y, scores, groups):
        if score is None:
            continue
        i = positions[group]
        counts[i, 0 if label else 1] += 1
        counts[i, 2 if label else 3] += int(score >= threshold)
    uncertainty = {'n_families': len(unique), 'requested_replicates': replicates, 'seed': seed,
                   'estimand': 'Observed-response TPR/FPR at frozen threshold; unavailable responses excluded from rates but retained in resampled families and coverage bounds.',
                   'limitations': 'Few families yield unstable intervals. A degenerate empirical interval, including zero observed errors, does not imply zero population risk. No interval when fewer than two families contribute the relevant observed class.'}
    samples = (np.random.default_rng(seed).multinomial(len(unique), np.full(len(unique), 1/len(unique)), size=replicates) @ counts
               if unique else np.zeros((replicates, 4), dtype=np.int64))
    for denominator, numerator, name in [(0, 2, 'tpr'), (1, 3, 'fpr')]:
        contributing = int(np.sum(counts[:, denominator] > 0))
        valid = samples[:, denominator] > 0
        values = samples[valid, numerator]/samples[valid, denominator]
        uncertainty[name] = {'contributing_families': contributing, 'valid_replicates': int(valid.sum()),
                             'ci95': np.quantile(values, [.025, .975]).tolist() if contributing >= 2 and len(values) else None}
    result['family_cluster_uncertainty'] = uncertainty
    return result


def paired_cluster_difference(y,a,b,groups,threshold_a,threshold_b,replicates=2000,seed=20260926):
    y=np.asarray(y);a=np.asarray(a);b=np.asarray(b);groups=np.asarray(groups)
    if not (len(y)==len(a)==len(b)==len(groups)):raise ValueError('Unpaired lengths')
    unique=np.unique(groups)
    if len(unique)<2:raise ValueError('At least two independent families required')
    indices={g:np.flatnonzero(groups==g) for g in unique}
    rng=np.random.default_rng(seed);diffs={'tpr':[],'fpr':[]}
    for _ in range(replicates):
        chosen=rng.choice(unique,len(unique),replace=True);ix=np.concatenate([indices[g] for g in chosen])
        for label,name in [(1,'tpr'),(0,'fpr')]:
            target=ix[y[ix]==label]
            if len(target):diffs[name].append(float(np.mean(a[target]>=threshold_a)-np.mean(b[target]>=threshold_b)))
    result={'n_families':len(unique),'requested_replicates':replicates,'seed':seed,'direction':'arm_a minus arm_b','limitations':'Family-clustered resampling preserves paired methods. Few families can still yield unstable or degenerate intervals.'}
    for label,name in [(1,'tpr'),(0,'fpr')]:
        mask=y==label
        result[name]={'difference':float(np.mean(a[mask]>=threshold_a)-np.mean(b[mask]>=threshold_b)) if mask.any() else None,'ci95':np.quantile(diffs[name],[.025,.975]).tolist() if diffs[name] else None,'valid_replicates':len(diffs[name])}
    return result


def disagreement_table(y,decisions):
    y=np.asarray(y)
    arms=list(decisions)
    if any(len(decisions[arm])!=len(y) for arm in arms):raise ValueError('Unpaired decision arrays')
    result={}
    for i,label in enumerate(y):
        if label not in [0,1]:raise ValueError('Only confirmed labels in paired taxonomy')
        key=' + '.join(arm for arm in arms if decisions[arm][i]) or 'none'
        row=result.setdefault(key,{'positive':0,'benign':0})
        row['positive' if label==1 else 'benign']+=1
    return result
