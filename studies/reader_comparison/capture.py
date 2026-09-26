"""Capture audited read sites from causal prefixes, once for all downstream arms.

Read-site JSON entries are bound to the episode hash and contain action_start / 
action_end character offsets into raw_response. Boundaries must be adjudicated
before capture; this program neither invents nor labels an action.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from contracts import fingerprint,validate_cell
from qwen_subject import QwenSubject
from smoke import write_json,digest


def generated_token_ends(tokenizer, ids, raw):
    ends=[]
    for stop in range(1,len(ids)+1):
        prefix=tokenizer.decode(ids[:stop],skip_special_tokens=False,clean_up_tokenization_spaces=False)
        # Byte fragments can decode to a temporary replacement character. They
        # do not establish a valid character boundary and are excluded.
        ends.append(len(prefix) if raw.startswith(prefix) else None)
    if ends and ends[-1]!=len(raw):raise ValueError('Token IDs do not reproduce the archived response')
    return ends


def read_positions(prompt_length, token_ends, start, end):
    if not 0<=start<end:raise ValueError('Invalid audited action interval')
    preceding=[i for i,e in enumerate(token_ends) if e is not None and e<=start]
    before=prompt_length+(preceding[-1] if preceding else -1)
    following=[i for i,e in enumerate(token_ends) if e is not None and e>=end]
    if not following:raise ValueError('Action end absent from trajectory')
    after=prompt_length+following[0]
    result={'end_prompt':prompt_length-1,'before_action':before,'during_action':(before+1+after)//2,'after_action':after}
    for offset in [32,64]:
        if before-offset>=0:result[f'before_action_{offset}']=before-offset
    return result


def main():
    import torch
    from safetensors.torch import save_file
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--episodes',type=Path,required=True);p.add_argument('--sites',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    cfg=json.loads(a.config.read_text());sites=json.loads(a.sites.read_text());subject=QwenSubject(cfg,dtype='float32');a.out.mkdir(parents=True,exist_ok=True)
    manifest={'identity':subject.identity,'sites_sha256':digest(a.sites),'layers':cfg['read_layers'],'capture':'each causal prefix separately, use_cache=False, subject adapter active','code_sha256':digest(__file__)}
    if (a.out/'manifest.json').exists() and json.loads((a.out/'manifest.json').read_text())!=manifest:raise ValueError('Changed capture provenance')
    write_json(a.out/'manifest.json',manifest)
    prefix_cache={}  # Identical causal prefixes have identical states, across seeds.
    for site in sites:
        ep=json.loads((a.episodes/(site['episode_id']+'.json')).read_text())
        if fingerprint(ep)!=site['episode_sha256'] or ep['identity']!=subject.identity:raise ValueError('Episode or checkpoint mismatch')
        target=a.out/site['episode_id'];target.mkdir(exist_ok=True)
        if (target/'complete.json').exists():
            done=json.loads((target/'complete.json').read_text())
            if done['manifest_sha256']!=fingerprint(manifest) or done['state_sha256']!=digest(target/'states.safetensors'):raise ValueError('Stale capture cache')
            continue
        ends=generated_token_ends(subject.tokenizer,ep['generated_ids'],ep['raw_response'])
        positions=read_positions(len(ep['prompt_ids']),ends,site['action_start'],site['action_end'])
        ids=ep['prompt_ids']+ep['generated_ids'];states={};records=[]
        for endpoint,position in positions.items():
            prefix=ids[:position+1]
            cache_key=tuple(prefix)
            if cache_key not in prefix_cache:
                prefix_cache[cache_key]=subject.capture(prefix,cfg['read_layers'],[position])
            captured=prefix_cache[cache_key]
            for layer,h in captured.items():
                key=f'{endpoint}:L{layer}';vector=h[0].contiguous().clone()  # safetensors forbids aliases across endpoint keys
                if not torch.isfinite(vector).all():raise ValueError('Nonfinite activation')
                states[key]=vector
                cell={'cell_id':f"{ep['episode_id']}:{key}",'state_key':key,'episode_id':ep['episode_id'],'family_id':site['family_id'],'split':site['split'],'endpoint':endpoint,'layer':layer,'position':position,'prefix_ids':prefix,'prefix_text':subject.tokenizer.decode(prefix,skip_special_tokens=False,clean_up_tokenization_spaces=False),'position_in_generated_output':position>=len(ep['prompt_ids']),'identity_sha256':fingerprint(subject.identity),'state_sha256':__import__('hashlib').sha256(vector.numpy().tobytes()).hexdigest()}
                validate_cell(cell,subject.identity,cfg['read_layers'])
                records.append(cell)
        save_file(states,str(target/'states.safetensors'))
        write_json(target/'cells.json',records)
        write_json(target/'complete.json',{'manifest_sha256':fingerprint(manifest),'state_sha256':digest(target/'states.safetensors'),'cells_sha256':digest(target/'cells.json'),'n_cells':len(records)})
        print(json.dumps({'episode_id':ep['episode_id'],'cells':len(records)}),flush=True)


if __name__=='__main__':main()
