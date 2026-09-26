"""Fresh paired continuations for a caller-registered single intervention site.

No automatic site selection, GPU launch, outcome adjudication, or inference of
misalignment mechanisms. Caller must bind this plan to development provenance.
"""
from contextlib import nullcontext
import math
from postblock_intervention import PostBlockEdit
from contracts import fingerprint


def run_site(subject, plan):
    import torch
    required={'prefix_ids','layer','position','mode','seeds','max_new_tokens','directions','doses','registration_sha256','identity'}
    if set(plan)!=required:raise ValueError('Incomplete or unexpected causal plan fields')
    if plan['identity']!=subject.identity:raise ValueError('Subject identity differs from plan')
    if not isinstance(plan['registration_sha256'],str) or (len(plan['registration_sha256'])!=64 or any(c not in '0123456789abcdef' for c in plan['registration_sha256'])):
        raise ValueError('External development registration hash required')
    ids=plan['prefix_ids'];seeds=plan['seeds'];doses=plan['doses']
    if not ids or any(type(i) is not int or i<0 for i in ids):raise ValueError('Invalid causal prefix')
    if not seeds or any(type(s) is not int or not 0<=s<2**63 for s in seeds) or len(set(seeds))!=len(seeds):raise ValueError('Invalid paired seed schedule')
    if not doses or any(type(d) not in (int,float) or not math.isfinite(d) or d==0 for d in doses) or len(set(doses))!=len(doses):raise ValueError('Nonzero registered doses required; sham is automatic')
    if type(plan['max_new_tokens']) is not int or not 1<=plan['max_new_tokens']<=2048:raise ValueError('Invalid continuation budget')
    if type(plan['layer']) is not int or not 0<=plan['layer']<len(subject.layers):raise ValueError('Invalid block')
    if not plan['directions'] or any(len(v)!=subject.d_model for v in plan['directions'].values()):raise ValueError('Direction width differs')
    model=subject.model
    if model.training:raise ValueError('Subject must be in evaluation mode')
    cache_mode=getattr(getattr(model,'generation_config',None),'cache_implementation',None)
    if cache_mode not in (None,'dynamic'):raise ValueError('Only fresh dynamic/default cache supported')
    device=next(model.parameters()).device
    if device.type not in ('cpu','cuda'):raise ValueError('Unqualified generation device')
    x=torch.tensor([ids],device=device,dtype=torch.long)
    devices=[device.index if device.index is not None else torch.cuda.current_device()] if device.type=='cuda' else []
    eos=subject.tokenizer.eos_token_id
    sampling={'max_new_tokens':plan['max_new_tokens'],'do_sample':True,'temperature':.7,'top_p':.95,'top_k':20,
              'use_cache':True,'num_beams':1,'num_return_sequences':1,'pad_token_id':eos}
    rows=[];checks=[]
    def generate(seed, edit):
        with torch.random.fork_rng(devices=devices),torch.inference_mode():
            torch.default_generator.manual_seed(seed)
            if devices:torch.cuda.default_generators[devices[0]].manual_seed(seed)
            with edit.attached(subject.layers[plan['layer']]) if edit else nullcontext():
                output=model.generate(input_ids=x.clone(),attention_mask=torch.ones_like(x),past_key_values=None,**sampling)
        if output.ndim!=2 or output.shape[0]!=1 or not torch.equal(output[0,:len(ids)],x[0]):raise ValueError('Generation changed supplied prefix')
        new=output[0,len(ids):].tolist()
        if not 0<len(new)<=plan['max_new_tokens']:raise ValueError('Continuation length violates budget')
        return {'generated_ids':new,'raw_response':subject.tokenizer.decode(new,skip_special_tokens=False),
                'completion_text':subject.tokenizer.decode(new,skip_special_tokens=True),
                'hit_token_budget':len(new)>=plan['max_new_tokens'],
                'ended_with_eos':bool(new) and new[-1] in (eos if isinstance(eos,list) else [eos]),
                'edits':edit.records if edit else []}
    def edit(direction,dose):
        return PostBlockEdit(direction,dose,prefix_length=len(ids),position=plan['position'],mode=plan['mode'])
    # Validate all directions before any generation; sham direction is arbitrary.
    for direction in plan['directions'].values():edit(direction,0)
    sham_direction=next(iter(plan['directions'].values()))
    # All replay checks must pass before any nonzero condition is generated.
    for seed in seeds:
        baseline=generate(seed,None);sham=generate(seed,edit(sham_direction,0))
        if baseline['generated_ids']!=sham['generated_ids']:raise ValueError('Zero-dose replay mismatch; nonzero runs prohibited')
        checks.append({'seed':seed,'identical_token_replay':True,'tokens':len(sham['generated_ids'])})
        rows.append({'seed':seed,'condition':'sham','dose':0.,**sham})
    for name,direction in plan['directions'].items():
        for dose in doses:
            for seed in seeds:rows.append({'seed':seed,'condition':name,'dose':dose,**generate(seed,edit(direction,dose))})
    return {'plan_sha256':fingerprint(plan),'plan':plan,'sampling':sampling,'zero_dose_checks':checks,'continuations':rows,
            'scope':'Fresh paired continuations only. Original episode outcome is not the causal baseline. Simulator/permission/quality/format/refusal adjudication and family-clustered effect analysis remain separate. No causal mechanism claim follows from generation success.'}
