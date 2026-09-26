"""Directional finite differences for the reference J-lens reduction on Qwen."""
import argparse
import json
import sys
import time
from pathlib import Path
from qwen_subject import QwenSubject
from smoke import write_json


def main():
    import torch
    from jlens.hooks import ActivationRecorder
    from jlens.fitting import valid_position_mask
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--seq-len',type=int,default=64);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(a.config.read_text());subject=QwenSubject(cfg,dtype='float32')
    torch.manual_seed(20260926)
    text='A team of researchers observed the growth of plants in several environments. They recorded temperature, rainfall, soil moisture, sunlight, and the height of each plant every morning. After collecting measurements for several months, the team compared the growth rates and considered possible explanations for the differences. The researchers then designed another experiment to test whether changes in sunlight caused the observed differences.'
    ids=subject.encode(text*4,max_length=a.seq_len);valid=valid_position_mask(ids.shape[1]).cuda()
    report={'identity':subject.identity,'seq_len':ids.shape[1],'input_ids':ids[0].tolist(),'estimator':'target-position sum / source-position mean, pinned reference','rows':[],'complete':False}
    with torch.no_grad(), ActivationRecorder(subject.layers,at=[63]) as rec:
        subject.forward(ids)
        wrapped=subject.unembed(rec.activations[63][:,-1])
        direct=subject.model(input_ids=ids,use_cache=False,logits_to_keep=1).logits[:,-1]
        parity=(wrapped-direct).abs().max().item()
    report['wrapper_logit_max_error']=parity
    if parity>1e-4:raise RuntimeError('Fitting wrapper differs from active subject model')
    del rec,wrapped,direct
    for layer in cfg['read_layers']:
        start=time.time()
        with ActivationRecorder(subject.layers,at=[layer,63],start_graph_at=layer) as rec:
            subject.forward(ids);source=rec.activations[layer];target=rec.activations[63]
            direction=torch.zeros_like(source);v=torch.randn(subject.d_model,device='cuda');v/=v.norm();direction[:,valid]=v
            c=torch.randn(subject.d_model,device='cuda');c/=c.norm()
            grad=torch.autograd.grad((target[:,valid].double()*c.double()).sum(),source)[0]
            predicted=(grad.double()*direction.double()).sum().item()/valid.sum().item()
        del rec,source,target,grad
        sweep=[]
        for epsilon in [0.03,0.1,0.3,1.0]:
            vals=[]
            for sign in [-1,1]:
                def perturb(_m,_i,out):
                    if isinstance(out,tuple):return (out[0]+sign*epsilon*direction,)+out[1:]
                    return out+sign*epsilon*direction
                handle=subject.layers[layer].register_forward_hook(perturb)
                try:
                    with torch.no_grad(),ActivationRecorder(subject.layers,at=[63]) as rec:
                        subject.forward(ids);vals.append(rec.activations[63][:,valid].double().clone())
                finally:handle.remove()
            fd=((vals[1]-vals[0])*c.double()).sum().item()/(2*epsilon*valid.sum().item())
            sweep.append({'epsilon':epsilon,'finite_difference':fd,'relative_error':abs(fd-predicted)/max(abs(fd),abs(predicted),1e-8)})
        passes=[r['relative_error']<=0.02 for r in sweep]
        row={'layer':layer,'predicted':predicted,'sweep':sweep,'passed':any(x and y for x,y in zip(passes,passes[1:])),'seconds':time.time()-start}
        report['rows'].append(row);write_json(a.out/'report.json',report);print(json.dumps(row),flush=True)
    report.update(complete=True,passed=all(r['passed'] for r in report['rows']),peak_cuda_bytes=torch.cuda.max_memory_allocated())
    write_json(a.out/'report.json',report)


if __name__=='__main__':main()
