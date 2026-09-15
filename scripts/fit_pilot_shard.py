"""Full-dimensional pinned-reference pilot, disjoint sharding and provenance-locked resume."""
import argparse,hashlib,json,logging,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,'/workspace/jacobian-lens')
def main():
    import torch
    from jlens.fitting import fit
    from gptoss_lens_model import load_model
    p=argparse.ArgumentParser();p.add_argument('--shard',type=int,required=True);p.add_argument('--dim-batch',type=int,required=True);p.add_argument('--stage-config',type=Path);a=p.parse_args()
    stage=json.loads(a.stage_config.read_text()) if a.stage_config else {'name':'fit-pilot','n_prompts':4,'shards':2,'max_seq_len':64}
    assert 0<=a.shard<stage['shards']
    gate=json.loads((ROOT/'configs/fit-pilot-gate.json').read_text())
    assert gate['numerics_passed'] and gate['positives']>=30 and gate['benign']>=30
    assert a.dim_batch==gate['dim_batch']
    corpus=ROOT/stage.get('corpus','configs/generic-corpus.json')
    entries=json.loads(corpus.read_text())['fit_prompts'][:stage['n_prompts']]
    if 'prompt_order_seed' in stage:
        import random
        random.Random(stage['prompt_order_seed']).shuffle(entries)
    entries=entries[a.shard::stage['shards']]
    out=ROOT/f"runs/{stage['name']}-{a.shard}";out.mkdir(parents=True,exist_ok=True)
    manifest={'shard':a.shard,'shards':stage['shards'],'prompt_ids':[x['id'] for x in entries],
              'corpus_sha256':hashlib.sha256(corpus.read_bytes()).hexdigest(),'dim_batch':a.dim_batch,
              'max_seq_len':stage['max_seq_len'],'source_layers':[7,15,21,22],'target_layer':23,'skip_first':16,
              'identity_sha256':hashlib.sha256((ROOT/'configs/identity-fp32.json').read_bytes()).hexdigest(),
              'reference_revision':'581d398613e5602a5af361e1c34d3a92ea82ba8e','scope':stage.get('scope','full-dimensional four-prompt engineering pilot; not a converged final lens')}
    path=out/'manifest.json'
    if path.exists():assert json.loads(path.read_text())==manifest,'Changed fit provenance'
    else:path.write_text(json.dumps(manifest,indent=2)+'\n')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    model=load_model(ROOT);started=time.time()
    lens=fit(model,[x['text'] for x in entries],source_layers=[7,15,21,22],target_layer=23,
             dim_batch=a.dim_batch,max_seq_len=stage['max_seq_len'],checkpoint_path=str(out/'checkpoint.pt'))
    temporary=out/'lens.tmp';lens.save(str(temporary),dtype=torch.float32);temporary.replace(out/'lens.pt')
    report={'n_prompts':lens.n_prompts,'seconds':time.time()-started,'lens_sha256':hashlib.sha256((out/'lens.pt').read_bytes()).hexdigest(),'peak_cuda_bytes':torch.cuda.max_memory_allocated()}
    (out/'complete.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
