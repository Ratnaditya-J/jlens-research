"""Engineering check of static FP8 quantization and GEMM; no study labels."""
import argparse
from pathlib import Path


def main():
    import torch
    import vllm
    from vllm import _custom_ops as ops
    from smoke import digest, write_json
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    torch.manual_seed(20260926)
    torch.backends.cuda.matmul.allow_tf32 = False
    cases = []
    for rows, inner, columns, scale in [(1, 256, 256, .025), (17, 512, 256, .05), (4, 256, 512, .004)]:
        x = torch.randn(rows, inner, device='cuda', dtype=torch.bfloat16)
        w = torch.randn(columns, inner, device='cuda', dtype=torch.bfloat16)
        sx = torch.tensor(scale, device='cuda', dtype=torch.float32)
        sw = torch.tensor(.02, device='cuda', dtype=torch.float32)
        qx, used_scale = ops.scaled_fp8_quant(x, sx)
        qw, _ = ops.scaled_fp8_quant(w, sw)
        ref_qx = (x.float()/sx).clamp(-448, 448).to(torch.float8_e4m3fn)
        ref_qw = (w.float()/sw).clamp(-448, 448).to(torch.float8_e4m3fn)
        exact_quant = torch.equal(qx.float(), ref_qx.float()) and torch.equal(qw.float(), ref_qw.float())
        reference = (ref_qx.float()*sx) @ (ref_qw.float()*sw).T
        actual = ops.cutlass_scaled_mm(qx, qw.T, sx, sw, torch.bfloat16).float()
        error = ((actual-reference).norm()/reference.norm()).item()
        cases.append({'shape':[rows,inner,columns], 'input_scale':scale,
                      'used_scale':used_scale.item(), 'exact_quantization':exact_quant,
                      'relative_l2':error, 'passed':exact_quant and used_scale.item()==sx.item() and error < .01})
    report = {'scope':'Standalone static FP8 operators, including saturation. Does not establish full-model correctness or judge quality.',
              'torch':torch.__version__, 'vllm':vllm.__version__, 'code_sha256':digest(__file__),
              'cases':cases, 'passed':all(c['passed'] for c in cases)}
    write_json(a.out, report)
    print(report, flush=True)
    if not report['passed']:
        raise SystemExit('Static FP8 preflight failed')


if __name__ == '__main__':
    main()
