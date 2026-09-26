"""Outcome-blind stability diagnostics; never select fit size on test outcomes."""
import argparse,json
from pathlib import Path
from contracts import fingerprint
from smoke import digest,write_json

def main():
 import torch
 p=argparse.ArgumentParser();p.add_argument('--lenses',nargs='+',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();loaded=[]
 torch.set_num_threads(4)
 for path in a.lenses:
  manifest=json.loads((path/'manifest.json').read_text());done=json.loads((path/'complete.json').read_text())
  if fingerprint(manifest)!=done['manifest_sha256'] or digest(path/'lens.pt')!=done['lens_sha256']:raise ValueError('Lens integrity mismatch')
  obj=torch.load(path/'lens.pt',map_location='cpu',weights_only=True)
  if obj['n_prompts']!=len(manifest['prompts']):raise ValueError('Fit count mismatch')
  if loaded:
   previous=loaded[-1][1]
   for key in ['identity','source_layers','target_layer','skip_first','max_seq_len','corpus_sha256','shuffle_seed','reference_revision']:
    if manifest[key]!=previous[key]:raise ValueError('Incompatible lens estimates')
   if manifest['prompts'][:len(previous['prompts'])]!=previous['prompts']:raise ValueError('Estimates are not nested')
  loaded.append((path,manifest,obj))
 if len(loaded)<2:raise ValueError('At least two nested estimates required')
 final=loaded[-1][2];rows=[]
 for _,_,obj in loaded[:-1]:
  for layer,J in obj['J'].items():
   ref=final['J'][layer].double();x=J.double();delta=x-ref
   rng=torch.Generator().manual_seed(20260926);directions=torch.randn((J.shape[1],64),generator=rng,dtype=torch.float64);z=x@directions;target=ref@directions
   rows.append({'n_prompts':obj['n_prompts'],'reference_n_prompts':final['n_prompts'],'layer':layer,'relative_frobenius_change':float(delta.norm()/ref.norm()),'matrix_cosine':float((x*ref).sum()/(x.norm()*ref.norm())),'isotropic_transport_mean_cosine':float(torch.nn.functional.cosine_similarity(z,target,dim=0).mean()),'isotropic_transport_relative_error':float((z-target).norm()/target.norm())})
 report={'identity':loaded[0][1]['identity'],'lenses':[{'n_prompts':obj['n_prompts'],'sha256':digest(path/'lens.pt')} for path,_,obj in loaded],'diagnostics':rows,'scope':'Finite-sample stability against the largest empirical estimate, not ground-truth Jacobian accuracy or semantic fidelity. Isotropic directions are synthetic engineering controls, not model activations. No behavior labels or held-out outcomes used.'}
 a.out.parent.mkdir(parents=True,exist_ok=True);write_json(a.out,report)
if __name__=='__main__':main()
