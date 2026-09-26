"""Oracle descriptions from saved subject vectors, using a separate reader model."""
import argparse
import hashlib
import json
from pathlib import Path
from contracts import fingerprint,validate_cell
from smoke import write_json,digest

PROMPT="An activation vector from layer {layer} of a language model is enclosed in activation tags: <activation>{char}</activation>. Produce distinct concepts that encode this activation, each as a '- ' bullet on its own line."


def carrier(tokenizer,layer):
    for code in range(0x3200,0x3400):
        char=chr(code);marker=tokenizer(char,add_special_tokens=False).input_ids
        if len(marker)!=1:continue
        ids=tokenizer.apply_chat_template([{'role':'user','content':PROMPT.format(layer=layer,char=char)}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
        if hasattr(ids,'keys'):ids=ids['input_ids']
        positions=[i for i,t in enumerate(ids) if t==marker[0]]
        if len(positions)==1:return ids,positions[0]
    raise ValueError('No unique marker in the full rendered carrier')


def main():
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import PeftModel,get_peft_model_state_dict
    from huggingface_hub import snapshot_download
    from safetensors import safe_open
    from safetensors.torch import load_file
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--captures',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--endpoint',default='before_action');p.add_argument('--batch-size',type=int,default=8);p.add_argument('--seed',type=int,default=20260926);a=p.parse_args()
    cfg=json.loads(a.config.read_text());capture_manifest=json.loads((a.captures/'manifest.json').read_text());identity=capture_manifest['identity']
    if identity['base']!=cfg['base'] or identity['adapter']!=cfg['subject_adapter']:raise ValueError('Wrong subject checkpoint for Oracle comparison')
    rows=[];vectors=[]
    for path in sorted(a.captures.glob('*/complete.json')):
        complete=json.loads(path.read_text());directory=path.parent
        if complete['manifest_sha256']!=fingerprint(capture_manifest) or complete['state_sha256']!=digest(directory/'states.safetensors') or complete['cells_sha256']!=digest(directory/'cells.json'):raise ValueError('Capture integrity failure')
        tensors=load_file(str(directory/'states.safetensors'))
        for cell in json.loads((directory/'cells.json').read_text()):
            if cell['endpoint']!=a.endpoint:continue
            validate_cell(cell,identity,cfg['oracle']['trained_layers'])
            h=tensors[cell['state_key']].float()
            if hashlib.sha256(h.numpy().tobytes()).hexdigest()!=cell['state_sha256']:raise ValueError('State hash mismatch')
            rows.append(cell);vectors.append(h)
    if not rows:raise ValueError('No eligible captured cells')
    # A reader must not get fresh random chances for identical underlying states.
    aliases={}; unique={}; kept_rows=[]; kept_vectors=[]
    for row,h in zip(rows,vectors):
        key=(row['layer'],row['state_sha256'])
        if key not in unique:
            unique[key]=row['cell_id'];kept_rows.append(row);kept_vectors.append(h)
        aliases.setdefault(unique[key],[]).append(row['cell_id'])
    rows,vectors=kept_rows,kept_vectors
    manifest={'subject_identity':identity,'capture_manifest_sha256':fingerprint(capture_manifest),'oracle':cfg['oracle'],'prompt':PROMPT,'reader_dtype':'bfloat16','reader_adapter_merged':False,'sampling':{'temperature':1.,'top_p':.95,'top_k':64,'max_new_tokens':256,'samples_per_cell':1,'batch_size':a.batch_size,'seed':a.seed},'ordered_cell_ids':[r['cell_id'] for r in rows],'identical_state_aliases':aliases,'endpoint':a.endpoint,'code_sha256':digest(__file__)}
    a.out.mkdir(parents=True,exist_ok=True)
    if (a.out/'manifest.json').exists() and json.loads((a.out/'manifest.json').read_text())!=manifest:raise ValueError('Changed Oracle inference provenance')
    write_json(a.out/'manifest.json',manifest)
    base=snapshot_download(repo_id=cfg['base']['repo'],revision=cfg['base']['revision'],allow_patterns=['*.json','*.jinja','*.txt','*.safetensors'])
    local=snapshot_download(repo_id=cfg['oracle']['repo'],revision=cfg['oracle']['revision'],allow_patterns=[cfg['oracle']['subfolder']+'/*'])
    tok=AutoTokenizer.from_pretrained(base)
    reader=AutoModelForCausalLM.from_pretrained(base,dtype=torch.bfloat16,device_map='cuda',attn_implementation='eager')
    adapter=Path(local)/cfg['oracle']['subfolder'];reader=PeftModel.from_pretrained(reader,str(adapter),is_trainable=False).eval()
    loaded=get_peft_model_state_dict(reader)
    with safe_open(str(adapter/'adapter_model.safetensors'),framework='pt',device='cpu') as source:
        if set(source.keys())!=set(loaded):raise ValueError('Oracle adapter key mismatch')
        for name in source.keys():
            if not torch.equal(loaded[name].detach().cpu(),source.get_tensor(name).to(loaded[name].dtype)):raise ValueError('Oracle adapter tensor mismatch')
    carriers={layer:carrier(tok,layer) for layer in cfg['oracle']['trained_layers']}
    contract_lengths={len(ids) for ids,_ in carriers.values()}
    if len(contract_lengths)!=1:raise ValueError('Carrier lengths differ; explicit padding validation required')
    for start in range(0,len(rows),a.batch_size):
        path=a.out/f'batch-{start:06d}.json'
        request={'manifest_sha256':fingerprint(manifest),'start':start,'cell_ids':[r['cell_id'] for r in rows[start:start+a.batch_size]],'seed':a.seed+start}
        if path.exists():
            if json.loads(path.read_text())['request_sha256']!=fingerprint(request):raise ValueError('Stale Oracle batch')
            continue
        cells=rows[start:start+a.batch_size];states=vectors[start:start+a.batch_size]
        ids=torch.tensor([carriers[c['layer']][0] for c in cells],device='cuda')
        with torch.no_grad():
            embeddings=reader.get_input_embeddings()(ids).clone()
            for i,(cell,h) in enumerate(zip(cells,states)):
                embeddings[i,carriers[cell['layer']][1]]=(cfg['oracle']['alpha']*h/h.norm().clamp_min(1e-9)).to('cuda',embeddings.dtype)
            mask=torch.ones_like(ids)
            if start==0:
                on=reader(inputs_embeds=embeddings[:1],attention_mask=mask[:1],use_cache=False,logits_to_keep=1).logits[:,-1].float()
                with reader.disable_adapter():off=reader(inputs_embeds=embeddings[:1],attention_mask=mask[:1],use_cache=False,logits_to_keep=1).logits[:,-1].float()
                delta=(on-off).abs().max().item()
                if delta<1e-4:raise ValueError('Oracle adapter appears inactive')
                write_json(a.out/'adapter-active-gate.json',{'max_logit_delta':delta,'subject_identity':identity,'reader_active_adapters':reader.active_adapters})
            torch.manual_seed(a.seed+start)
            outputs=reader.generate(inputs_embeds=embeddings,attention_mask=mask,do_sample=True,temperature=1.,top_p=.95,top_k=64,max_new_tokens=256,pad_token_id=tok.eos_token_id)
        results=[]
        eos=reader.generation_config.eos_token_id;eos={eos} if isinstance(eos,int) else set(eos)
        for cell,output in zip(cells,outputs):
            token_ids=output.tolist();stops=[i for i,t in enumerate(token_ids) if t in eos]
            if stops:token_ids=token_ids[:stops[0]+1]
            results.append({'cell_id':cell['cell_id'],'alias_cell_ids':aliases[cell['cell_id']],'state_sha256':cell['state_sha256'],'status':'ok','text':tok.decode(token_ids,skip_special_tokens=True),'generated_ids':token_ids,'truncated':not stops and len(token_ids)>=256})
        write_json(path,{'request_sha256':fingerprint(request),'request':request,'results':results})
        print(json.dumps({'completed_cells':min(start+a.batch_size,len(rows)),'total_cells':len(rows)}),flush=True)


if __name__=='__main__':main()
