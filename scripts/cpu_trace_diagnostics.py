"""Full sampled-token J displays for the unchanged held-out casebook; secondary."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,'/workspace/jacobian-lens')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
    tmp=p.with_suffix('.partial');tmp.write_text(json.dumps(x)+'\n');tmp.replace(p)
def main():
    import torch,numpy as np
    from safetensors.torch import load_file
    from tokenizers import Tokenizer
    from jlens.lens import JacobianLens
    torch.set_num_threads(4)
    source=ROOT/'runs/cpu-readout';sm=json.loads((source/'manifest.json').read_text())
    for name,digest in sm['files_sha256'].items():assert sha(source/name)==digest
    weights=load_file(str(source/'native-readout.safetensors'));head=weights['lm_head.weight'].float();norm=weights['model.norm.weight'].float();del weights
    eps=json.loads((source/'config.json').read_text())['rms_norm_eps']
    tok=Tokenizer.from_file(str(source/'tokenizer.json'));decode=lambda ids:tok.decode(ids,skip_special_tokens=False)
    lp=ROOT/'runs/fit64-merged/lens.pt';lens=JacobianLens.load(str(lp));assert lens.n_prompts==64
    def logits(states,layer):
        z=lens.transport(states.float(),layer)
        z=z*torch.rsqrt(z.pow(2).mean(-1,keepdim=True)+eps)
        return (norm*z)@head.T
    summaryp=ROOT/'reports/final-comparison/summary.json';summary=json.loads(summaryp.read_text())
    cfg=json.loads((ROOT/'configs/fresh-v1.json').read_text());indices={r['episode_id']:i for i,r in enumerate(cfg['episodes'])}
    out=ROOT/'runs/casebook-full-traces';out.mkdir(parents=True,exist_ok=True)
    cal=ROOT/'runs/fresh-calibration';lock=json.loads((cal/'lock.json').read_text())
    for name,digest in lock['artifacts'].items():assert sha(cal/name)==digest
    native=np.load(cal/'probe-native.npz');direction=native['native_direction'];bias=float(native['native_intercept'].reshape(-1)[0])
    auditp=ROOT/'reports/final-comparison/action-audit.json';actions={r['episode_id']:r for r in json.loads(auditp.read_text())['rows']}
    words=['cheat','hack','reward','evaluation','test','assert','equal','override','exit','terminate','deceive','bypass','correct','solve','return','class']
    candidate_ids=sorted({i for w in words for i in tok.encode(' '+w,add_special_tokens=False).ids})
    manifest={'summary_sha256':sha(summaryp),'selection':summary['casebook_ids'],'lens_sha256':sha(lp),'native_readout_manifest_sha256':sha(source/'manifest.json'),'probe_lock_sha256':sha(cal/'lock.json'),'action_audit_sha256':sha(auditp),'script_sha256':sha(Path(__file__)),'layers':[7,15,21,22],'positions':'Every saved live state before generated token j; no state after the final generated token','scope':'Post-test secondary display diagnostic. Fixed primary probe applied off-endpoint without recalibration; top tokens and candidate ranks are not independently interpreted J-view flags. No threshold or primary result changes.','parity_gate':{'top20_set_overlap_min':.95,'stored_top20_logit_max_abs_error':1e-4},'candidate_ids':candidate_ids}
    mp=out/'manifest.json'
    if mp.exists():assert json.loads(mp.read_text())==manifest
    else:write(mp,manifest)
    completed=[]
    for eid in manifest['selection']:
        folder=out/eid;folder.mkdir(exist_ok=True);done=folder/'complete.json'
        if done.exists():
            d=json.loads(done.read_text());assert d['manifest_sha256']==sha(mp)
            for name,digest in d['files_sha256'].items():assert sha(folder/name)==digest
            completed.append(eid);continue
        epfile=ROOT/'runs/fresh'/eid/'episode.json';ep=json.loads(epfile.read_text());sf=epfile.with_name('activations.safetensors');assert sha(sf)==ep['activation_sha256']
        states=load_file(str(sf));processed=ROOT/f'runs/fresh-processed-{indices[eid]%4}'/eid
        saved=json.loads((processed/'complete.json').read_text())
        for name in ['positions.json','readouts.json']:assert sha(processed/name)==saved['files_sha256'][name]
        positions=json.loads((processed/'positions.json').read_text());old=json.loads((processed/'readouts.json').read_text());checks=[]
        with torch.no_grad():
            for view in old:
                j=positions['positions'][str(view['offset'])]['sample_index']
                for layer in view['layers']:
                    l=layer['layer'];scores=logits(states[f'layer_{l}'][j],l)
                    ids=[r['id'] for r in layer['top_tokens']];expected=torch.tensor([r['logit'] for r in layer['top_tokens']]);error=float((scores[ids]-expected).abs().max());overlap=len(set(ids)&set(scores.topk(20).indices.tolist()))/20
                    check={'offset':view['offset'],'layer':l,'max_logit_error':error,'top20_overlap':overlap};checks.append(check)
                    assert error<=1e-4 and overlap>=.95,check
            write(folder/'parity.json',checks)
            n=len(ep['generated_token_ids']);raw=states[f"layer_{lock['selected']['layer']}"].numpy().astype(np.float64);projections=raw@direction+bias;prob=1/(1+np.exp(-np.clip(projections,-700,700)))
            assert raw.shape[0]==n
            metadata={'episode_id':eid,'episode_sha256':sha(epfile),'activation_sha256':sha(sf),'primary_sample_index':positions['primary_sample_index'],'action':actions[eid],'probe_scores':prob.tolist(),'probe_flags':(prob>=lock['probe_threshold']).tolist(),'generated_token_ids':ep['generated_token_ids'],'generated_token_text':[decode([i]) for i in ep['generated_token_ids']],'candidate_tokens':{i:decode([i]) for i in candidate_ids}}
            write(folder/'trajectory.json',metadata)
            start=time.time()
            for l in manifest['layers']:
                rows=[]
                for first in range(0,n,16):
                    scores=logits(states[f'layer_{l}'][first:first+16],l);values,ids=scores.topk(20,dim=-1)
                    ranks=torch.stack([(scores>scores[:,i,None]).sum(-1)+1 for i in candidate_ids],dim=-1)
                    for k in range(len(scores)):
                        rows.append({'sample_index':first+k,'top_tokens':[{'id':i,'text':decode([i]),'logit':v} for i,v in zip(ids[k].tolist(),values[k].tolist())],'candidate_ranks':ranks[k].tolist()})
                write(folder/f'layer-{l}.json',rows)
        names=['trajectory.json','parity.json']+[f'layer-{l}.json' for l in manifest['layers']]
        write(done,{'manifest_sha256':sha(mp),'files_sha256':{name:sha(folder/name) for name in names},'display_seconds':time.time()-start})
        completed.append(eid);write(out/'progress.json',{'completed':len(completed),'total':len(manifest['selection'])});print('trace',len(completed),eid,flush=True)
    write(out/'complete.json',{'case_complete_sha256':{eid:sha(out/eid/'complete.json') for eid in completed},'manifest_sha256':sha(mp)})
if __name__=='__main__':main()
