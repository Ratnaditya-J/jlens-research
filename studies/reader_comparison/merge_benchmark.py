"""Measure optional FP32 LoRA-merge drift/speed; does not silently change identity."""
import argparse
import json
import time
from pathlib import Path
from qwen_subject import QwenSubject
from smoke import write_json


def main():
    import torch
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    cfg=json.loads(a.config.read_text());s=QwenSubject(cfg,dtype='float32')
    prompts=['The researcher measured sunlight and soil moisture to understand how plants grow. The results suggest that','The software engineer tests the calculation on several independent examples before releasing the update. The tests show that']
    ids=[s.encode(t,max_length=64) for t in prompts]
    report={'unmerged_identity':s.identity,'scope':'engineering benchmark only; merging changes the execution identity and requires fresh fitting/capture','conditions':{}}
    logits={}
    for arm in ['unmerged','merged']:
        if arm=='merged':s.model=s.model.merge_and_unload(safe_merge=True).eval()
        values=[];start=time.time()
        with torch.no_grad():
            for x in ids:values.append(s.model(input_ids=x,use_cache=False,logits_to_keep=1).logits[:,-1].float().cpu())
        torch.cuda.synchronize();elapsed=time.time()-start;logits[arm]=values
        # Equal generated-token count prevents EOS variation from biasing speed.
        with torch.no_grad():
            s.model.generate(input_ids=ids[0],attention_mask=torch.ones_like(ids[0]),do_sample=False,min_new_tokens=8,max_new_tokens=8,use_cache=True,pad_token_id=s.tokenizer.eos_token_id)
        sequence_lengths=[]
        def trace(_m,args,kwargs):
            h=args[0] if args else kwargs['hidden_states']
            if len(sequence_lengths)<8:sequence_lengths.append(h.shape[1])
        handle=s.layers[0].register_forward_pre_hook(trace,with_kwargs=True)
        torch.cuda.synchronize();start=time.time()
        with torch.no_grad():
            output=s.model.generate(input_ids=ids[0],attention_mask=torch.ones_like(ids[0]),do_sample=False,min_new_tokens=64,max_new_tokens=64,use_cache=True,pad_token_id=s.tokenizer.eos_token_id)
        torch.cuda.synchronize();seconds=time.time()-start
        handle.remove()
        report['conditions'][arm]={'prefill_seconds':elapsed,'generation_seconds_64_tokens':seconds,'tokens_per_second':64/seconds,'first_decoder_sequence_lengths':sequence_lengths,'generated_ids':output[0,ids[0].shape[1]:].tolist()}
        if arm=='merged':
            report['logit_max_abs_error']=max((x-y).abs().max().item() for x,y in zip(logits['unmerged'],values))
            report['top1_matches']=all(x.argmax(-1).item()==y.argmax(-1).item() for x,y in zip(logits['unmerged'],values))
        write_json(a.out,report)
        print(json.dumps({'condition':arm,**report['conditions'][arm]}),flush=True)


if __name__=='__main__':main()
