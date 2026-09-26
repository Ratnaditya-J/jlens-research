"""Pinned subject / Oracle compatibility pilot. Not a misalignment evaluation."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def main():
    import torch
    from huggingface_hub import snapshot_download
    from peft import PeftModel
    import transformers
    from transformers import AutoModelForImageTextToText, AutoModelForCausalLM, AutoTokenizer

    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--subject-dtype',choices=['bfloat16','float32'],default='bfloat16')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(args.config.read_text())
    torch.manual_seed(20260926)
    torch.backends.cuda.matmul.allow_tf32 = False
    started = time.time()
    base = snapshot_download(**{'repo_id': cfg['base']['repo'], 'revision': cfg['base']['revision']}, ignore_patterns=['*.bin','*.msgpack','*.h5'])
    adapter = snapshot_download(repo_id=cfg['subject_adapter']['repo'], revision=cfg['subject_adapter']['revision'], allow_patterns=['adapter_config.json','adapter_model.safetensors'])
    oracle = snapshot_download(repo_id=cfg['oracle']['repo'], revision=cfg['oracle']['revision'], allow_patterns=[cfg['oracle']['subfolder']+'/*'])
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForImageTextToText.from_pretrained(base, dtype=getattr(torch,args.subject_dtype), device_map='cuda', attn_implementation='eager')
    model = PeftModel.from_pretrained(model, adapter, is_trainable=False).eval()
    base_model = model.get_base_model()
    blocks = base_model.model.language_model.layers
    matched = [n for n,_ in model.named_parameters() if 'lora_' in n]
    assert matched, 'Subject adapter did not attach'
    layers = cfg['read_layers']
    assert set(layers) <= set(cfg['oracle']['trained_layers'])
    texts = [
        'The bird on the branch is a bright red cardinal. The bird is',
        'After several hours in the oven, the baker takes out a loaf of fresh bread. The food is',
        'The astronomer points the telescope at the red planet Mars. The planet is',
        'A doctor explains that the patient has a broken arm and needs a cast. The injury is',
    ]
    states = {}
    records = []
    for arm in ['subject','base']:
        for i, text in enumerate(texts):
            ids = tok(text, return_tensors='pt').input_ids.cuda()
            store = {}
            def make_hook(layer):
                def hook(_m, _i, out):
                    h = out[0] if isinstance(out, tuple) else out
                    store[layer] = h[0,-1].detach().float().cpu()
                return hook
            handles = [blocks[l].register_forward_hook(make_hook(l)) for l in layers]
            from contextlib import nullcontext
            try:
                with torch.no_grad(), (model.disable_adapter() if arm == 'base' else nullcontext()):
                    output = model(input_ids=ids, use_cache=False, logits_to_keep=1)
                    top = torch.topk(output.logits[0,-1].float(), 5).indices.tolist()
            finally:
                for handle in handles: handle.remove()
            for layer,h in store.items():
                assert torch.isfinite(h).all() and h.norm() > 0
                states[f'{arm}:{i}:{layer}'] = h
            records.append({'arm':arm,'item':i,'text':text,'ids':ids[0].tolist(),'top_next_tokens':tok.convert_ids_to_tokens(top)})
    del model, base_model, blocks, output
    gc.collect(); torch.cuda.empty_cache()
    torch.save(states,args.out/'states.pt')
    write_json(args.out/'capture.json',{'config_sha256':digest(args.config),'subject_dtype':args.subject_dtype,'transformers':transformers.__version__,'torch':torch.__version__,'adapter_parameters':len(matched),'records':records,'seconds':time.time()-started})
    # A separate unmodified base + Oracle. Subject weights are never merged into it.
    reader = AutoModelForCausalLM.from_pretrained(base,dtype=torch.bfloat16,device_map='cuda',attn_implementation='eager')
    reader = PeftModel.from_pretrained(reader,str(Path(oracle)/cfg['oracle']['subfolder']),is_trainable=False).eval()
    results=[]
    for key,h in states.items():
        arm,item,layer=key.split(':'); layer=int(layer)
        for code in range(0x3200,0x3400):
            char=chr(code); marker=tok(char,add_special_tokens=False).input_ids
            if len(marker)!=1: continue
            prompt=f"An activation vector from layer {layer} of a language model is enclosed in activation tags: <activation>{char}</activation>. Produce distinct concepts that encode this activation, each as a '- ' bullet on its own line."
            ids=tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
            if hasattr(ids,'keys'):ids=ids['input_ids']
            slots=[i for i,t in enumerate(ids) if t==marker[0]]
            if len(slots)==1:break
        else: raise RuntimeError('No unique single-token carrier marker')
        with torch.no_grad():
            embeds=reader.get_input_embeddings()(torch.tensor([ids],device='cuda')).clone()
            embeds[0,slots[0]]= (cfg['oracle']['alpha']*h/h.norm()).to('cuda',embeds.dtype)
            output=reader.generate(inputs_embeds=embeds,attention_mask=torch.ones((1,len(ids)),dtype=torch.long,device='cuda'),do_sample=False,max_new_tokens=128,pad_token_id=tok.eos_token_id)
        results.append({'key':key,'carrier_ids':ids,'marker_position':slots[0],'reader_text':tok.decode(output[0],skip_special_tokens=True)})
        write_json(args.out/'oracle.json',results)
        print(json.dumps(results[-1]),flush=True)
    write_json(args.out/'complete.json',{'seconds':time.time()-started,'config_sha256':digest(args.config),'states_sha256':digest(args.out/'states.pt'),'scope':'engineering semantic sanity only; greedy reader differs from final sampling protocol','peak_cuda_bytes':torch.cuda.max_memory_allocated()})


if __name__ == '__main__':
    main()
