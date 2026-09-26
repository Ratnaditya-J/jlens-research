"""Training-activation fit stability, with disjoint fitting-corpus halves.

No task outcome labels or held-out rows are used to choose or compare fits.
The primary32 estimate stays fixed regardless of this diagnostic.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
from contracts import fingerprint
from smoke import digest, write_json


def summary(a, b):
    an=np.linalg.norm(a,axis=1);bn=np.linalg.norm(b,axis=1)
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or np.any(an==0) or np.any(bn==0):
        raise ValueError('Nonfinite or zero transported activation')
    cosine=np.sum(a*b,axis=1)/(an*bn)
    relative=np.linalg.norm(a-b,axis=1)/bn
    return {'n_unique_states':len(a),'cosine_quantiles':dict(zip(['min','p10','median','p90','max'],np.quantile(cosine,[0,.1,.5,.9,1]).tolist())),
            'relative_error_quantiles':dict(zip(['min','p10','median','p90','max'],np.quantile(relative,[0,.1,.5,.9,1]).tolist())),
            'aggregate_relative_error':float(np.linalg.norm(a-b)/np.linalg.norm(b))}


def main():
    import torch
    p=argparse.ArgumentParser()
    for name in ['first-half','second-shard','third-shard','primary','features','out']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('Preserve prior stability report')
    torch.set_num_threads(4)
    sources={};loaded=[]
    for folder in [a.first_half,a.second_shard,a.third_shard,a.primary]:
        manifest=json.loads((folder/'manifest.json').read_text());done=json.loads((folder/'complete.json').read_text())
        if fingerprint(manifest)!=done['manifest_sha256'] or digest(folder/'lens.pt')!=done['lens_sha256']:
            raise ValueError('Lens integrity mismatch')
        obj=torch.load(folder/'lens.pt',map_location='cpu',weights_only=True)
        if obj['n_prompts']!=len(manifest['prompts']):raise ValueError('Fit count mismatch')
        for filename in ['manifest.json','complete.json','lens.pt']:sources[str((folder/filename).resolve())]=digest(folder/filename)
        loaded.append((manifest,obj))
    first,second,third,primary=loaded
    if [o['n_prompts'] for _,o in loaded]!=[16,8,8,32]:raise ValueError('Expected registered16+8+8 fit')
    prompts=[q for m,_ in loaded[:3] for q in m['prompts']]
    if len(set(prompts))!=32 or prompts!=primary[0]['prompts']:raise ValueError('Corpus halves are not disjoint or do not match primary')
    for m,_ in loaded[:3]:
        for key in ['identity','source_layers','target_layer','skip_first','max_seq_len','corpus_sha256','shuffle_seed','reference_revision']:
            if m[key]!=primary[0][key]:raise ValueError('Incompatible fit settings')
    fm=json.loads((a.features/'manifest.json').read_text())
    if fm['identity']!=primary[0]['identity'] or fm['lens_sha256']!=digest(a.primary/'lens.pt') or fm['feature_sha256']!=digest(a.features/'features.npz'):
        raise ValueError('Feature source differs')
    arrays=np.load(a.features/'features.npz',allow_pickle=False)
    rows=[]
    for layer in primary[0]['source_layers']:
        indices={}
        for i,r in enumerate(fm['rows']):
            if r['split']=='train' and r['layer']==layer:
                state=np.ascontiguousarray(arrays['X_raw'][i],dtype=np.float32)
                if hashlib.sha256(state.tobytes()).hexdigest()!=r['state_sha256']:
                    raise ValueError('Raw training state hash differs')
                indices.setdefault(r['state_sha256'],i)
        if not indices:raise ValueError('No training states at layer')
        x=torch.from_numpy(arrays['X_raw'][list(indices.values())].astype(np.float64))
        j1=first[1]['J'][layer].double();j2=(second[1]['J'][layer].double()+third[1]['J'][layer].double())/2
        j32=primary[1]['J'][layer].double()
        recomposed=(j1+j2)/2
        error=float((recomposed-j32).norm()/j32.norm())
        if error>1e-6:raise ValueError('Primary matrix does not match weighted shards')
        z1=(x@j1.T).numpy();z2=(x@j2.T).numpy();z32=(x@j32.T).numpy()
        rows.append({'layer':layer,'first16_vs_primary32':summary(z1,z32),'disjoint16_vs16':summary(z1,z2),'primary_recomposition_relative_error':error,'training_state_set_sha256':fingerprint(sorted(indices))})
        print(json.dumps(rows[-1]),flush=True)
    for path in [a.features/'manifest.json',a.features/'features.npz',Path(__file__)]:sources[str(path.resolve())]=digest(path)
    report={'identity':fm['identity'],'endpoint':next(r['endpoint'] for r in fm['rows'] if r['split']=='train'),
            'diagnostics':rows,'source_sha256':sources,'runtime':{'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__},
            'scope':'Descriptive stability on unique training activation vectors only. No behavioral labels or held-out rows analyzed. Disjoint halves refer to lens-fitting corpus passages, not independent task episodes. Nested primary shares both halves; its agreement is optimistic. Vector agreement does not establish token-rank stability, semantic faithfulness, convergence to a population Jacobian, or misalignment coverage. No primary fit or detector selection changed.'}
    write_json(a.out,report)


if __name__=='__main__':main()
