"""Explicit post-block edits for batch-one cached generation.

This primitive does not select sites/doses, generate continuations, or establish
causal effects. Each condition must start a fresh forward pass and fresh cache.
"""
from contextlib import contextmanager
import math


class PostBlockEdit:
    def __init__(self, direction, dose, *, prefix_length, position, mode='single'):
        import torch
        if mode not in ('single','persistent'):raise ValueError('Unknown intervention mode')
        if type(prefix_length) is not int or type(position) is not int or not 0<=position<prefix_length:
            raise ValueError('Invalid prefix site')
        if not math.isfinite(dose):raise ValueError('Nonfinite dose')
        v=torch.as_tensor(direction,dtype=torch.float64).detach().clone()
        if v.ndim!=1 or not torch.isfinite(v).all() or v.norm()==0:raise ValueError('Invalid direction')
        self.direction=v/v.norm();self.dose=float(dose)
        self.prefix_length=prefix_length;self.position=position;self.mode=mode
        self.calls=0;self.records=[];self.used=False

    def __call__(self, module, inputs, output):
        import torch
        hidden=output[0] if isinstance(output,tuple) else output
        if not isinstance(hidden,torch.Tensor) or hidden.ndim!=3 or hidden.shape[0]!=1:
            raise ValueError('Only batch-one residual tensors are supported')
        if hidden.shape[-1]!=len(self.direction) or not hidden.is_floating_point():raise ValueError('Wrong activation coordinates')
        if self.calls==0:
            if hidden.shape[1]!=self.prefix_length:raise ValueError('Fresh full-prefix prefill required')
            site=self.position
        else:
            if hidden.shape[1]!=1:raise ValueError('Cached single-token decoding required; do not reuse full prefixes')
            if self.mode=='single':
                self.calls+=1
                return output
            site=0
        self.calls+=1
        state=hidden[0,site]
        if not torch.isfinite(state).all():raise ValueError('Nonfinite intervention state')
        delta=(self.direction*self.dose).to(device=hidden.device,dtype=hidden.dtype)
        if self.dose==0:
            # Exact identity, including tuple metadata and tensor aliasing.
            edited=output;actual=torch.zeros_like(state)
        else:
            value=hidden.clone();value[0,site]=state+delta
            actual=value[0,site].double()-state.double()
            if not torch.isfinite(value[0,site]).all():raise ValueError('Nonfinite edited activation')
            edited=(value,*output[1:]) if isinstance(output,tuple) else value
        self.records.append({'forward_call':self.calls,'position_in_call':site,'phase':'prefill' if self.calls==1 else 'decode',
            'mode':self.mode,'requested_signed_absolute_l2_dose':self.dose,
            'actual_delta_l2':float(actual.double().norm()),'state_l2':float(state.double().norm()),
            'activation_dtype':str(hidden.dtype)})
        return edited

    @contextmanager
    def attached(self, block):
        if self.used:raise ValueError('Each continuation condition needs a fresh edit and cache')
        self.used=True
        handle=block.register_forward_hook(self)
        completed=False
        try:
            yield self
            completed=True
        finally:
            handle.remove()
            if completed and not self.records:raise ValueError('Registered intervention site was never visited')
