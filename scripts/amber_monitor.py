"""Reusable frozen AMBER fits, extending the native development pipelines.

No calibration/test fitting, no executable pickle, no in-sample efficacy claim.
"""
import hashlib
import json
import sys
import warnings
import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

VERSION='amber-monitor-provider-v1'
FIELDS={'context':{'prompt'},'output':{'prompt','final_answer','action_trace'},
        'raw_cot':{'prompt','final_answer','action_trace','scratchpad'},
        'paraphrased_cot':{'prompt','final_answer','action_trace','scratchpad'}}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def text(view,arm):
    if not isinstance(view,dict) or set(view)!=FIELDS[arm]:raise ValueError('text view violates arm allowlist')
    for field,value in view.items():
        if field=='action_trace':
            if not isinstance(value,list) or any(not isinstance(v,str) for v in value):raise ValueError('invalid trace')
        elif not isinstance(value,str):raise ValueError('view must contain text')
    return json.dumps(view,sort_keys=True,ensure_ascii=False)


def predict(artifact,values):
    if artifact['version']!=VERSION or artifact['sklearn_version']!=sklearn.__version__:
        raise ValueError('provider/runtime drift')
    if artifact['kind']=='activation':
        matrix=np.asarray(values,dtype=np.float64)
    else:
        vectorizer=TfidfVectorizer(ngram_range=(1,2),min_df=1,max_features=20000,vocabulary=artifact['vocabulary'])
        vectorizer.idf_=np.asarray(artifact['idf'],dtype=np.float64)
        matrix=vectorizer.transform([text(v,artifact['arm']) for v in values])
    weights=np.asarray(artifact['weights'],dtype=np.float64)
    if matrix.ndim!=2 or matrix.shape[1]!=len(weights):raise ValueError('feature shape drift')
    scores=np.asarray(matrix@weights+artifact['intercept']).ravel()
    if not np.isfinite(scores).all():raise ValueError('nonfinite prediction')
    return scores.tolist()


def fit(kind,arm,rows):
    if kind not in ('text','activation') or (kind=='text' and arm not in FIELDS):raise ValueError('unknown kind/arm')
    if kind=='activation' and arm!='activation':raise ValueError('activation fit has wrong arm')
    ids=[row['episode_id'] for row in rows]
    if not rows or len(set(ids))!=len(ids):raise ValueError('empty or duplicated fitting rows')
    if any(row['split']!='train' for row in rows):raise ValueError('only prespecified training rows may enter fit')
    if any(type(row['label']) is not bool for row in rows):raise ValueError('explicit boolean training labels required')
    if len({row['label'] for row in rows})!=2:raise ValueError('both classes required')
    y=np.asarray([int(row['label']) for row in rows])
    values=[row['value'] for row in rows]
    artifact={'version':VERSION,'kind':kind,'arm':arm,'sklearn_version':sklearn.__version__,
              'training_sha256':digest(rows),'training_count':len(rows),'positive_count':int(y.sum()),
              'fit_settings':{'C':1.,'max_iter':3000,'solver':'lbfgs','random_state':20260915},
              'claim_license':'frozen_fit_only_no_efficacy_claim'}
    if kind=='activation':
        raw=np.asarray(values,dtype=np.float64)
        if raw.ndim!=2 or not raw.shape[1] or not np.isfinite(raw).all():raise ValueError('invalid activation matrix')
        scaler=StandardScaler();matrix=scaler.fit_transform(raw)
    else:
        vectorizer=TfidfVectorizer(ngram_range=(1,2),min_df=1,max_features=20000)
        matrix=vectorizer.fit_transform([text(v,arm) for v in values])
        artifact.update(vocabulary={k:int(v) for k,v in vectorizer.vocabulary_.items()},idf=vectorizer.idf_.tolist())
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        classifier=LogisticRegression(**artifact['fit_settings']).fit(matrix,y)
    weights=classifier.coef_[0];intercept=float(classifier.intercept_[0])
    if kind=='activation':
        weights=weights/scaler.scale_;intercept-=float(np.dot(weights,scaler.mean_))
    artifact.update(weights=weights.tolist(),intercept=intercept)
    replay=np.asarray(predict(artifact,values));reference=classifier.decision_function(matrix)
    error=float(np.max(np.abs(replay-reference)))
    if error>=1e-8:raise ValueError('portable score replay failed')
    return {'artifact':artifact,'artifact_sha256':digest(artifact),'native_margin_max_difference':error,
            'scope':'fit/export parity only; calibration and held-out evaluation must be separate'}


def main():
    request=json.load(sys.stdin)
    if request['operation']=='fit':result=fit(request['kind'],request['arm'],request['rows'])
    elif request['operation']=='predict':result={'scores':predict(request['artifact'],request['values'])}
    else:raise ValueError('unknown operation')
    print(json.dumps(result,allow_nan=False,sort_keys=True))


if __name__=='__main__':main()
