"""Fit a disjoint shard of a shuffled generic corpus without outcome access."""
import argparse,json,logging,random,time
from pathlib import Path
from contracts import fingerprint
from qwen_subject import QwenSubject
from smoke import write_json,digest

def main():
 import torch
 from jlens.fitting import fit
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--gate',type=Path,required=True);p.add_argument('--corpus',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--dim-batch',type=int,default=4);p.add_argument('--max-seq-len',type=int,default=128);p.add_argument('--milestones',default='1,4,8,16,32');p.add_argument('--start-index',type=int,default=0);a=p.parse_args()
 cfg=json.loads(a.config.read_text());gate=json.loads(a.gate.read_text());corpus=json.loads(a.corpus.read_text());entries=corpus['fit_prompts'].copy();random.Random(20260926).shuffle(entries);entries=entries[a.start_index:];milestones=[int(x) for x in a.milestones.split(',')]
 if not gate.get('complete') or not gate.get('passed'):raise ValueError('Numeric validation failed')
 if milestones!=sorted(set(milestones)) or max(milestones)>len(entries):raise ValueError('Invalid milestones')
 a.out.mkdir(parents=True,exist_ok=True);subject=QwenSubject(cfg,dtype='float32')
 if subject.identity!=gate['identity']:raise ValueError('Wrong subject numeric gate')
 manifest={'identity':subject.identity,'source_layers':cfg['read_layers'],'target_layer':63,'skip_first':16,'max_seq_len':a.max_seq_len,'dim_batch':a.dim_batch,'corpus_sha256':digest(a.corpus),'prompts':[e['id'] for e in entries[:max(milestones)]],'shuffle_seed':20260926,'start_index':a.start_index,'reference_revision':'581d398613e5602a5af361e1c34d3a92ea82ba8e','milestones':milestones,'scope':'Generic corpus fitting; task labels and evaluation trajectories excluded'}
 path=a.out/'manifest.json'
 if path.exists() and json.loads(path.read_text())!=manifest:raise ValueError('Changed fitting provenance')
 write_json(path,manifest);logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(message)s')
 for n in milestones:
  dest=a.out/str(n);dest.mkdir(exist_ok=True)
  if (dest/'complete.json').exists():continue
  start=time.time();lens=fit(subject,[e['text'] for e in entries[:n]],source_layers=cfg['read_layers'],target_layer=63,dim_batch=a.dim_batch,max_seq_len=a.max_seq_len,checkpoint_path=str(a.out/'checkpoint.pt'))
  if lens.n_prompts!=n:raise ValueError('Skipped fit prompt; inspect corpus')
  lens.save(str(dest/'lens.pt'),dtype=torch.float32);write_json(dest/'manifest.json',dict(manifest,prompts=manifest['prompts'][:n]))
  write_json(dest/'complete.json',{'seconds_increment':time.time()-start,'n_prompts':n,'lens_sha256':digest(dest/'lens.pt'),'peak_cuda_bytes':torch.cuda.max_memory_allocated(),'manifest_sha256':fingerprint(json.loads((dest/'manifest.json').read_text()))})
  print(json.dumps({'completed_milestone':n}),flush=True)
if __name__=='__main__':main()
