"""Checkpoint-locked J-space transport and two explicitly named token readouts."""
import argparse
import hashlib
import json
from pathlib import Path
from contracts import fingerprint,validate_cell
from qwen_subject import QwenSubject
from smoke import write_json,digest


def main():
    import torch
    from safetensors.torch import load_file,save_file
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--captures',type=Path,required=True);p.add_argument('--lens',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--endpoint',default='before_action');a=p.parse_args()
    cfg=json.loads(a.config.read_text());cm=json.loads((a.captures/'manifest.json').read_text());lm=json.loads((a.lens/'manifest.json').read_text());done=json.loads((a.lens/'complete.json').read_text())
    if cm['identity']!=lm['identity'] or fingerprint(lm)!=done['manifest_sha256'] or digest(a.lens/'lens.pt')!=done['lens_sha256']:raise ValueError('Lens/capture checkpoint or artifact mismatch')
    subject=QwenSubject(cfg,dtype='float32')
    if subject.identity!=lm['identity']:raise ValueError('Loaded subject differs from fitted checkpoint')
    obj=torch.load(a.lens/'lens.pt',map_location='cpu',weights_only=True);jac={int(k):v.cuda().float() for k,v in obj['J'].items()}
    manifest={'identity':subject.identity,'capture_manifest_sha256':fingerprint(cm),'lens_sha256':done['lens_sha256'],'endpoint':a.endpoint,'primary':'native W_U final_norm(Jh)','secondary':'magnitude_free (W_U J h) / row_norm(W_U J)','stored_top_k':100,'primary_display_top_k':10,'n_fit_prompts':obj['n_prompts'],'code_sha256':digest(__file__)}
    a.out.mkdir(parents=True,exist_ok=True)
    if (a.out/'manifest.json').exists() and json.loads((a.out/'manifest.json').read_text())!=manifest:raise ValueError('Changed J-lens readout provenance')
    write_json(a.out/'manifest.json',manifest)
    weights=subject.base.get_output_embeddings().weight
    denominator={}
    with torch.no_grad():
        for layer,J in jac.items():
            chunks=[]
            for start in range(0,len(weights),4096):chunks.append((weights[start:start+4096].float()@J).norm(dim=1).clamp_min(1e-9))
            denominator[layer]=torch.cat(chunks)
        for path in sorted(a.captures.glob('*/complete.json')):
            directory=path.parent;complete=json.loads(path.read_text())
            if complete['manifest_sha256']!=fingerprint(cm) or complete['state_sha256']!=digest(directory/'states.safetensors') or complete['cells_sha256']!=digest(directory/'cells.json'):raise ValueError('Capture corruption')
            rows=json.loads((directory/'cells.json').read_text());states=load_file(str(directory/'states.safetensors'));out=a.out/directory.name;out.mkdir(exist_ok=True)
            if (out/'complete.json').exists():
                prior=json.loads((out/'complete.json').read_text())
                if prior['manifest_sha256']!=fingerprint(manifest) or prior['readouts_sha256']!=digest(out/'readouts.json') or prior['jspace_sha256']!=digest(out/'jspace.safetensors'):raise ValueError('Stale J-lens output')
                continue
            transported={};results=[]
            for row in rows:
                if row['endpoint']!=a.endpoint:continue
                validate_cell(row,subject.identity,list(jac))
                h=states[row['state_key']].float()
                if hashlib.sha256(h.numpy().tobytes()).hexdigest()!=row['state_sha256']:raise ValueError('State identity mismatch')
                z=jac[row['layer']]@h.cuda();transported[row['state_key']]=z.cpu().contiguous()
                scores={'native':subject.unembed(z),'magnitude_free':(weights.float()@z)/denominator[row['layer']]}
                readouts={}
                for name,score in scores.items():
                    if not torch.isfinite(score).all():raise ValueError('Nonfinite lens readout')
                    values,ids=torch.topk(score,100)
                    readouts[name]={'token_ids':ids.tolist(),'tokens':[subject.tokenizer.decode([i],skip_special_tokens=False,clean_up_tokenization_spaces=False) for i in ids.tolist()],'scores':values.tolist()}
                results.append({'cell_id':row['cell_id'],'state_sha256':row['state_sha256'],'status':'ok','readouts':readouts})
            if not results:continue
            save_file(transported,str(out/'jspace.safetensors'));write_json(out/'readouts.json',results)
            write_json(out/'complete.json',{'manifest_sha256':fingerprint(manifest),'readouts_sha256':digest(out/'readouts.json'),'jspace_sha256':digest(out/'jspace.safetensors')})
            print(json.dumps({'episode_id':directory.name,'cells':len(results)}),flush=True)


if __name__=='__main__':main()
