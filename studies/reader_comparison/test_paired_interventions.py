import unittest
from types import SimpleNamespace
try:
    import torch
except ImportError:
    torch=None
from paired_interventions import run_site


@unittest.skipIf(torch is None,'Torch-specific tests run in the separate CPU lens-audit environment')
class PairedContinuationTest(unittest.TestCase):
    def fixture(self):
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__();self.weight=torch.nn.Parameter(torch.zeros(1));self.block=torch.nn.Identity();self.calls=[];self.corrupt=False
            def generate(self,**kwargs):
                assert kwargs['past_key_values'] is None
                self.calls.append({'draw':float(torch.rand(())),'past':kwargs['past_key_values']})
                x=kwargs['input_ids'];h=self.block(torch.zeros(1,x.shape[1],2));a=int(h.sum())+20
                self.block(torch.zeros(1,1,2));b=21
                if self.corrupt and len(self.calls)==2:b=22
                return torch.cat([x,torch.tensor([[a,b]])],dim=1)
        model=Model().eval();tok=SimpleNamespace(eos_token_id=99,decode=lambda ids,**kwargs:str(ids))
        subject=SimpleNamespace(identity={'checkpoint':'toy'},model=model,tokenizer=tok,layers=[model.block],d_model=2)
        plan={'identity':subject.identity,'prefix_ids':[1,2],'layer':0,'position':1,'mode':'single','seeds':[11,13],
              'max_new_tokens':2,'directions':{'probe':[1.,0.],'random':[0.,1.]},'doses':[-1.,1.],'registration_sha256':'a'*64}
        return subject,plan

    def test_paired_seeds_fresh_cache_and_rng_restoration(self):
        subject,plan=self.fixture();state=torch.random.get_rng_state().clone();out=run_site(subject,plan)
        self.assertTrue(torch.equal(state,torch.random.get_rng_state()))
        self.assertEqual(len(out['zero_dose_checks']),2);self.assertEqual(len(out['continuations']),10)
        self.assertEqual(len(subject.model.calls),12)
        draws=[r['draw'] for r in subject.model.calls]
        self.assertEqual(draws[0],draws[1]);self.assertEqual(draws[2],draws[3])
        self.assertEqual(draws[4:6],[draws[0],draws[2]])
        self.assertTrue(all(c['past'] is None for c in subject.model.calls))
        self.assertTrue(all(len(r['edits'])==1 for r in out['continuations']))
        self.assertFalse(subject.model.block._forward_hooks)

    def test_zero_dose_mismatch_prevents_any_nonzero_run(self):
        subject,plan=self.fixture();subject.model.corrupt=True
        with self.assertRaisesRegex(ValueError,'Zero-dose replay mismatch'):run_site(subject,plan)
        self.assertEqual(len(subject.model.calls),2);self.assertFalse(subject.model.block._forward_hooks)

    def test_invalid_direction_is_rejected_before_generation(self):
        subject,plan=self.fixture();plan['directions']['bad']=[0.,0.]
        with self.assertRaisesRegex(ValueError,'Invalid direction'):run_site(subject,plan)
        self.assertFalse(subject.model.calls)

    def test_persistent_mode_and_static_cache_rejection(self):
        subject,plan=self.fixture();plan['mode']='persistent';out=run_site(subject,plan)
        self.assertTrue(all(len(r['edits'])==2 for r in out['continuations']))
        subject,plan=self.fixture();subject.model.generation_config=SimpleNamespace(cache_implementation='static')
        with self.assertRaisesRegex(ValueError,'fresh dynamic/default'):run_site(subject,plan)
        self.assertFalse(subject.model.calls)
