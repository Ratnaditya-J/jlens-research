"""Validate provenance, checksums and weighted merging of full-dimensional shards."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'/workspace/jacobian-lens')
def main():
    import torch
    from jlens.lens import JacobianLens
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('shards',type=Path,nargs='+');a=p.parse_args()
    manifests=[];lenses=[];seen=set();sources=[]
    for directory in a.shards:
        m=json.loads((directory/'manifest.json').read_text());c=json.loads((directory/'complete.json').read_text())
        digest=hashlib.sha256((directory/'lens.pt').read_bytes()).hexdigest()
        assert digest==c['lens_sha256']
        assert not seen.intersection(m['prompt_ids']),'Overlapping fitting prompts'
        seen.update(m['prompt_ids'])
        if manifests:
            for k in ('corpus_sha256','dim_batch','max_seq_len','source_layers','target_layer','skip_first','identity_sha256','reference_revision'):
                assert m[k]==manifests[0][k],f'Incompatible {k}'
        lens=JacobianLens.load(str(directory/'lens.pt'))
        assert lens.n_prompts==c['n_prompts']==len(m['prompt_ids'])
        assert all(j.shape==(lens.d_model,lens.d_model) and torch.isfinite(j).all() for j in lens.jacobians.values())
        manifests.append(m);lenses.append(lens);sources.append({'directory':str(directory),'sha256':digest,'n_prompts':lens.n_prompts,'seconds':c['seconds']})
    merged=JacobianLens.merge(lenses);metrics={}
    for layer,matrix in merged.jacobians.items():
        manual=sum(l.jacobians[layer]*l.n_prompts for l in lenses)/merged.n_prompts
        error=(matrix-manual).abs().max().item();assert error==0
        metrics[layer]={'weighted_merge_max_error':error,'frobenius_norm':matrix.norm().item(),
                        'max_shard_relative_distance':max((l.jacobians[layer]-matrix).norm().item()/matrix.norm().item() for l in lenses)}
    a.output.mkdir(parents=True,exist_ok=True)
    merged.save(str(a.output/'lens.pt'),dtype=torch.float32)
    report={'n_prompts':merged.n_prompts,'sources':sources,'metrics':metrics,
            'lens_sha256':hashlib.sha256((a.output/'lens.pt').read_bytes()).hexdigest(),
            'gate':'checksums, provenance, finite full matrices and exact weighted merging pass; convergence and readout validity still require evaluation'}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
