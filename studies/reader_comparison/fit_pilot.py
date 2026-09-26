"""Full-dimensional checkpoint-specific J-lens pilot, gated by numeric validation."""
import argparse
import json
import logging
import time
from pathlib import Path
from contracts import fingerprint
from qwen_subject import QwenSubject
from smoke import write_json, digest


def main():
    import torch
    from jlens.fitting import fit
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--gate',type=Path,required=True);p.add_argument('--corpus',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--n-prompts',type=int,default=1);p.add_argument('--dim-batch',type=int,default=4);a=p.parse_args()
    cfg=json.loads(a.config.read_text());gate=json.loads(a.gate.read_text())
    if not gate.get('complete') or not gate.get('passed'):raise ValueError('Numeric validation did not pass')
    corpus=json.loads(a.corpus.read_text());entries=corpus['fit_prompts'][:a.n_prompts]
    if len(entries)!=a.n_prompts:raise ValueError('Insufficient independent fit passages')
    a.out.mkdir(parents=True,exist_ok=True)
    subject=QwenSubject(cfg,dtype='float32')
    if subject.identity!=gate['identity']:raise ValueError('Numeric gate applies to a different subject')
    manifest={'identity':subject.identity,'source_layers':cfg['read_layers'],'target_layer':63,'skip_first':16,'max_seq_len':64,'dim_batch':a.dim_batch,'corpus_sha256':digest(a.corpus),'prompts':[e['id'] for e in entries],'reference_revision':'581d398613e5602a5af361e1c34d3a92ea82ba8e','scope':'full dimensional engineering fit; convergence not established'}
    path=a.out/'manifest.json'
    if path.exists() and json.loads(path.read_text())!=manifest:raise ValueError('Changed fitting provenance')
    write_json(path,manifest)
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(message)s')
    start=time.time()
    lens=fit(subject,[e['text'] for e in entries],source_layers=cfg['read_layers'],target_layer=63,dim_batch=a.dim_batch,max_seq_len=64,checkpoint_path=str(a.out/'checkpoint.pt'))
    lens.save(str(a.out/'lens.pt'),dtype=torch.float32)
    write_json(a.out/'complete.json',{'seconds':time.time()-start,'n_prompts':lens.n_prompts,'lens_sha256':digest(a.out/'lens.pt'),'peak_cuda_bytes':torch.cuda.max_memory_allocated(),'manifest_sha256':fingerprint(manifest)})


if __name__=='__main__':main()
