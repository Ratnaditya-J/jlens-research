"""Validate actual reference residual reductions; run only with exclusive GPU access.

Uses pre-final-norm block 23, target-position sum and source-position mean.
No behavior labels or learned lens are used. Each result is checkpointed.
"""
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get('JLENS_REFERENCE', '/workspace/jacobian-lens'))

def main():
    import torch
    from jlens.hooks import ActivationRecorder
    from jlens.fitting import valid_position_mask
    from gptoss_lens_model import load_model
    out = ROOT/'runs/lens-numerics'
    out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(314159)
    model = load_model(ROOT)
    corpus_path = ROOT/'configs/generic-corpus.json'
    corpus = json.loads(corpus_path.read_text())
    report = {'kind': 'reference_reduction_numerical_validation',
              'corpus_sha256': hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
              'identity_sha256': hashlib.sha256((ROOT/'configs/identity-fp32.json').read_bytes()).hexdigest(),
              'threshold': 'two adjacent epsilon values with relative error <= 0.02 for each layer/context',
              'rows': [], 'complete': False}
    def save():
        tmp = out/'report.tmp'
        tmp.write_text(json.dumps(report, indent=2)+'\n')
        tmp.replace(out/'report.json')
    save()
    for length in (64, 256):
        prompt = next(x for x in corpus['validation_prompts']
                      if model.encode(x['text'], max_length=length).shape[1] == length)
        ids = model.encode(prompt['text'], max_length=length)
        valid = valid_position_mask(length).to('cuda')
        # Readout parity also checks this wrapper still executes active LoRA.
        with torch.no_grad(), ActivationRecorder(model.layers, at=[23]) as rec:
            model.forward(ids)
            logits = model.unembed(rec.activations[23][:, -1])
            direct = model.peft_model(ids, use_cache=False).logits[:, -1]
            parity = (logits-direct).abs().max().item()
        del logits, direct, rec
        for layer in (7, 15, 21, 22):
            started = time.time()
            with ActivationRecorder(model.layers, at=[layer, 23], start_graph_at=layer) as rec:
                model.forward(ids)
                source, target = rec.activations[layer], rec.activations[23]
                v = torch.randn(model.d_model, device='cuda')
                v /= v.norm()
                c = torch.randn(model.d_model, device='cuda')
                c /= c.norm()
                # Perturb all valid source positions by v/n, yielding the
                # source mean in the paper's Jacobian estimator.
                direction = torch.zeros_like(source)
                direction[:, valid] = v / valid.sum()
                scalar = (target[:, valid] * c).sum()
                grad = torch.autograd.grad(scalar, source)[0]
                predicted = (grad * direction).sum().item()
            del scalar, grad, source, target, rec
            gc.collect(); torch.cuda.empty_cache()
            sweep = []
            for epsilon in (.01, .03, .1, .3):
                values = []
                for sign in (-1, 1):
                    def perturb(module, args, output):
                        if isinstance(output, tuple):
                            return (output[0] + sign*epsilon*direction,) + output[1:]
                        return output + sign*epsilon*direction
                    handle = model.layers[layer].register_forward_hook(perturb)
                    try:
                        with torch.no_grad(), ActivationRecorder(model.layers, at=[23]) as rec:
                            model.forward(ids)
                            values.append((rec.activations[23][:, valid]*c).sum().item())
                    finally:
                        handle.remove()
                    del rec
                fd = (values[1]-values[0])/(2*epsilon)
                error = abs(fd-predicted)/max(abs(fd), abs(predicted), 1e-8)
                sweep.append({'epsilon': epsilon, 'finite_difference': fd, 'relative_error': error})
            passes = [x['relative_error'] <= .02 for x in sweep]
            row = {'layer': layer, 'seq_len': length, 'prompt_id': prompt['id'],
                   'directional_derivative': predicted, 'sweep': sweep,
                   'readout_parity_max_error': parity,
                   'passed': parity <= 1e-4 and any(a and b for a,b in zip(passes,passes[1:])),
                   'seconds': time.time()-started,
                   'peak_cuda_bytes': torch.cuda.max_memory_allocated()}
            report['rows'].append(row); save(); print(json.dumps(row), flush=True)
            del direction, c, v
    report['complete'] = True
    report['passed'] = all(row['passed'] for row in report['rows'])
    report['limitations'] = 'Two generic contexts and one random projection per layer. No fitted-lens quality or behavioral performance established. Failed finite differences require rounding/routing diagnosis.'
    save()

if __name__ == '__main__': main()
