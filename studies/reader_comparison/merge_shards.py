"""Merge disjoint exact-checkpoint lens shards, validating the frozen 32-prompt plan."""
import argparse,json,random
from pathlib import Path
from contracts import fingerprint
from smoke import write_json,digest

def validate_manifests(manifests,planned_ids):
 for m in manifests[1:]:
  for key in ['identity','source_layers','target_layer','skip_first','max_seq_len','dim_batch','corpus_sha256','shuffle_seed','reference_revision']:
   if m[key]!=manifests[0][key]:raise ValueError('Incompatible shard '+key)
 ids=[p for m in manifests for p in m['prompts']]
 if len(ids)!=len(set(ids)):raise ValueError('Overlapping fit passages')
 if ids!=planned_ids:raise ValueError('Shards do not exactly cover the frozen ordered fit corpus')
 return ids

def main():
 import torch
 from jlens.lens import JacobianLens
 p=argparse.ArgumentParser();p.add_argument('--shards',nargs='+',type=Path,required=True);p.add_argument('--corpus',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();corpus=json.loads(a.corpus.read_text());entries=corpus['fit_prompts'].copy();random.Random(20260926).shuffle(entries);planned=[e['id'] for e in entries[:32]];manifests=[json.loads((d/'manifest.json').read_text()) for d in a.shards];ids=validate_manifests(manifests,planned);lenses=[];sources=[]
 for directory,m in zip(a.shards,manifests):
  done=json.loads((directory/'complete.json').read_text())
  if digest(directory/'lens.pt')!=done['lens_sha256'] or fingerprint(m)!=done['manifest_sha256'] or digest(a.corpus)!=m['corpus_sha256']:raise ValueError('Shard/corpus provenance mismatch')
  lens=JacobianLens.load(str(directory/'lens.pt'))
  if lens.n_prompts!=len(m['prompts']) or lens.n_prompts!=done['n_prompts']:raise ValueError('Shard weighting mismatch')
  if not all(torch.isfinite(j).all() for j in lens.jacobians.values()):raise ValueError('Nonfinite shard')
  lenses.append(lens);sources.append({'lens_sha256':done['lens_sha256'],'manifest_sha256':fingerprint(m),'n_prompts':lens.n_prompts})
 merged=JacobianLens.merge(lenses);assert merged.n_prompts==32
 manifest={k:manifests[0][k] for k in ['identity','source_layers','target_layer','skip_first','max_seq_len','dim_batch','corpus_sha256','shuffle_seed','reference_revision']};manifest.update(prompts=ids,shards=sources,scope='32-passage full-dimensional mean, exact same pinned subject; disjoint shards combined with prompt-count weighting. Floating-point summation order differs from serial accumulation.',merge_code_sha256=digest(__file__))
 a.out.mkdir(parents=True,exist_ok=True)
 if (a.out/'complete.json').exists():raise ValueError('Do not overwrite completed primary lens')
 merged.save(str(a.out/'lens.pt'),dtype=torch.float32);write_json(a.out/'manifest.json',manifest);write_json(a.out/'complete.json',{'n_prompts':32,'lens_sha256':digest(a.out/'lens.pt'),'manifest_sha256':fingerprint(manifest)})
if __name__=='__main__':main()
