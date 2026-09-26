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
