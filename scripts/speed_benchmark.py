"""Measured acceleration checks, preserving residual and reference reduction semantics."""
import gc, hashlib, json, math, os, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, '/workspace/jacobian-lens')

def main():
    import torch
    from jlens.hooks import ActivationRecorder
    from jlens.fitting import valid_position_mask
    from gptoss_lens_model import load_model
    model=load_model(ROOT);torch.manual_seed(314159)
    out=ROOT/'runs/speed-benchmark';out.mkdir(parents=True,exist_ok=True)
    report={'cache_rows':[], 'fitting_batches':[], 'complete':False,
            'cache_tolerance':{'max_logit_absolute_error':.001,'max_residual_relative_rms_error':.00001},
            'fitting_scope':'32 output rows, 64 generic tokens, all four source layers; extrapolation is not measured full-fit time'}
    def save():
        tmp=out/'report.tmp';tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(out/'report.json')
    save()
    for case in json.loads((ROOT/'configs/cache-benchmark.json').read_text())['cases']:
        initial=torch.tensor([case['initial_token_ids']],device='cuda')
        continuation=case['generated_token_ids'][:32]
        captures={}
        def hook(layer):
            def record(module,args,result):
                captures[layer]=(result[0] if isinstance(result,tuple) else result)[:,-1].detach().clone()
            return record
        handles=[model.layers[l].register_forward_hook(hook(l)) for l in (7,15,21,22)]
        ids=initial;past=None;max_logit=0.;max_residual=0.;cached_seconds=0.;full_seconds=0.
        with torch.no_grad():
            for step in range(len(continuation)+1):
                torch.cuda.synchronize();t=time.time()
                full=model.peft_model(ids,attention_mask=torch.ones_like(ids),use_cache=False,logits_to_keep=1)
                torch.cuda.synchronize();full_seconds+=time.time()-t
                full_logits=full.logits[:,-1].clone();full_states=dict(captures);del full
                torch.cuda.synchronize();t=time.time()
                cached=model.peft_model(ids if past is None else ids[:,-1:],attention_mask=torch.ones_like(ids),
                                       past_key_values=past,use_cache=True,logits_to_keep=1)
                torch.cuda.synchronize();cached_seconds+=time.time()-t
                max_logit=max(max_logit,(cached.logits[:,-1]-full_logits).abs().max().item())
                for layer in full_states:
                    delta=(captures[layer]-full_states[layer]).square().mean().sqrt()
                    denom=full_states[layer].square().mean().sqrt().clamp_min(1e-8)
                    max_residual=max(max_residual,(delta/denom).item())
                past=cached.past_key_values
                del cached,full_logits,full_states
                if step<len(continuation):ids=torch.cat([ids,torch.tensor([[continuation[step]]],device='cuda')],dim=1)
        for handle in handles:handle.remove()
        row={'episode_id':case['episode_id'],'initial_tokens':initial.shape[1],'steps':len(continuation)+1,
             'max_logit_error':max_logit,'max_residual_relative_rms_error':max_residual,
             'cached_seconds':cached_seconds,'full_seconds':full_seconds,'speedup':full_seconds/cached_seconds,
             'passed':max_logit<=.001 and max_residual<=.00001}
        report['cache_rows'].append(row);save();print(json.dumps(row),flush=True)
        del past,ids,initial,captures
        gc.collect();torch.cuda.empty_cache()
    report['cache_passed']=all(r['passed'] for r in report['cache_rows']) and len(report['cache_rows'])>=3
    corpus=json.loads((ROOT/'configs/generic-corpus.json').read_text())
    ids=model.encode(corpus['fit_prompts'][0]['text'],max_length=64)
    positions=valid_position_mask(ids.shape[1]).nonzero(as_tuple=True)[0].to('cuda')
    baseline=None
    def trial(batch):
        torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();started=time.time()
        collected={l:[] for l in (7,15,21,22)}
        with ActivationRecorder(model.layers,at=[7,15,21,22,23],start_graph_at=7) as rec:
            model.forward(ids.expand(batch,-1))
            target=rec.activations[23];cotangent=torch.zeros_like(target)
            for start in range(0,32,batch):
                count=min(batch,32-start);cotangent.zero_()
                for b in range(count):cotangent[b,positions,start+b]=1
                grads=torch.autograd.grad(target,[rec.activations[l] for l in collected],cotangent,retain_graph=start+batch<32)
                for layer,gradient in zip(collected,grads):collected[layer].append(gradient[:count,positions].float().mean(1).cpu())
                del grads
        torch.cuda.synchronize();elapsed=time.time()-started
        rows={l:torch.cat(v) for l,v in collected.items()}
        return rows,elapsed,torch.cuda.max_memory_allocated()
    for batch in (1,2,4,8):
        try:
            rows,elapsed,peak=trial(batch)
            if baseline is None:baseline=rows
            error=max(((rows[l]-baseline[l]).square().mean().sqrt()/baseline[l].square().mean().sqrt().clamp_min(1e-8)).item() for l in rows)
            row={'dim_batch':batch,'seconds_for_32_rows':elapsed,'estimated_seconds_per_2880_row_prompt':elapsed*90,
                 'peak_cuda_bytes':peak,'relative_rms_error_vs_batch1':error,'passed':error<=.0001}
            del rows
        except torch.cuda.OutOfMemoryError:
            row={'dim_batch':batch,'passed':False,'error':'CUDA out of memory'}
        report['fitting_batches'].append(row);save();print(json.dumps(row),flush=True)
        gc.collect();torch.cuda.empty_cache()
        if 'error' in row:break
    report['complete']=True;save()

if __name__=='__main__':main()
