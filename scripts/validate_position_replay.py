"""Exclusive GPU stage: parity at every declared detector position, never execute code."""
import argparse,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from gptoss_lens_model import load_model

def main():
    import torch
    from safetensors.torch import load_file
    p=argparse.ArgumentParser();p.add_argument('episodes',type=Path);p.add_argument('positions',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    manifest=json.loads(a.positions.read_text());a.output.mkdir(parents=True,exist_ok=True)
    spec={'positions_sha256':hashlib.sha256(a.positions.read_bytes()).hexdigest(),'identity_sha256':hashlib.sha256((ROOT/'configs/identity-fp32.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'relative_rms_tolerance':1e-5,'layers':[7,15,21,22]}
    lock=a.output/'manifest.json'
    if lock.exists():assert json.loads(lock.read_text())==spec,'changed replay provenance'
    else:lock.write_text(json.dumps(spec,indent=2)+'\n')
    model=load_model(ROOT);capture={};handles=[]
    def hook(layer):
        def fn(module,args,out):capture[layer]=(out[0] if isinstance(out,tuple) else out)[:,-1].detach().cpu()
        return fn
    for layer in spec['layers']:handles.append(model.layers[layer].register_forward_hook(hook(layer)))
    for row in manifest['rows']:
        if 'unavailable' in row:continue
        out=a.output/(row['episode_id']+'.json')
        if out.exists():continue
        directory=a.episodes/row['episode_id'];epfile=directory/'episode.json';statefile=directory/'activations.safetensors'
        assert hashlib.sha256(epfile.read_bytes()).hexdigest()==row['episode_sha256']
        assert hashlib.sha256(statefile.read_bytes()).hexdigest()==row['activation_sha256']
        ep=json.loads(epfile.read_text());assert ep['identity_sha256']==spec['identity_sha256'];states=load_file(str(statefile));checks=[]
        for layer in spec['layers']:assert states[f'layer_{layer}'].shape==(len(ep['generated_token_ids']),model.d_model)
        for offset,position in row['positions'].items():
            if not position['available']:continue
            j=position['sample_index'];ids=ep['initial_token_ids']+ep['generated_token_ids'][:j]
            assert len(ids)-1==position['absolute_residual_token_index']
            with torch.no_grad():model.forward(torch.tensor([ids],device='cuda'))
            for layer in spec['layers']:
                live=states[f'layer_{layer}'][j].float();replay=capture[layer][0].float();error=replay-live
                rms=(error.square().mean().sqrt()/live.square().mean().sqrt().clamp_min(1e-8)).item()
                checks.append({'offset':offset,'layer':layer,'sample_index':j,'relative_rms':rms,'max_absolute_error':error.abs().max().item(),'passed':rms<=spec['relative_rms_tolerance']})
        result={'episode_id':row['episode_id'],'runtime_use_cache':ep['runtime_use_cache'],'checks':checks,'passed':all(x['passed'] for x in checks),'time':time.time()}
        tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(out)
        print(json.dumps({'episode_id':row['episode_id'],'passed':result['passed']}),flush=True)
    for handle in handles:handle.remove()
if __name__=='__main__':main()
