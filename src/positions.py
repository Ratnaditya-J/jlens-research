"""Outcome- and detector-blind alignment of submitted code to saved causal states."""
from src.source_parser import extract_code_and_files

def source_line_positions(episode, decode):
    """Outcome-blind source map for later external action localization only."""
    ids=episode['generated_token_ids'];text=decode(ids)
    result={'episode_id':episode['episode_id'],'lines':[],
            'scope':'Retrospective source map; never exposed to detector inputs or used to select scored positions'}
    if text!=episode['generated_text']:return {**result,'unavailable':'tokenizer decode differs'}
    start,reason=code_onset(text)
    if reason:return {**result,'unavailable':reason}
    code,_=extract_code_and_files(text.split('<|channel|>final<|message|>',1)[-1])
    import hashlib
    result['code_sha256']=hashlib.sha256(code.encode()).hexdigest()
    targets=[];offset=start
    for number,line in enumerate(code.splitlines(keepends=True),1):
        if line.strip():targets.append((number,offset+len(line)-len(line.lstrip())))
        offset+=len(line)
    previous=''
    for end in range(1,len(ids)+1):
        prefix=decode(ids[:end])
        if not text.startswith(prefix) or not prefix.startswith(previous):
            return {**result,'lines':[],'unavailable':'nonmonotonic token decoding'}
        for number,char in targets:
            if len(previous)<=char<len(prefix):
                result['lines'].append({'source_line':number,'character_offset':char,'before_statement_sample_index':end-1,'token_straddles_statement_boundary':len(previous)<char})
        previous=prefix
        if len(result['lines'])==len(targets):break
    if len(result['lines'])!=len(targets):return {**result,'lines':[],'unavailable':'unmapped source lines'}
    return result

def code_onset(text):
    marker='<|channel|>final<|message|>'
    base=text.index(marker)+len(marker) if marker in text else 0
    submitted=text[base:]
    code,extra=extract_code_and_files(submitted)
    if extra:return None,'multiple-file action unsupported'
    if not code:return None,'empty code'
    # Restrict primary alignment to an unambiguous structured submission.
    if '```' not in submitted and '<file' not in submitted:return None,'unstructured submission'
    start=submitted.find(code)
    if start<0 or submitted.find(code,start+1)>=0:return None,'code substring not unique'
    return base+start,None

def position_manifest(episode,decode):
    ids=episode['generated_token_ids'];text=decode(ids)
    result={'episode_id':episode['episode_id'],'identity_sha256':episode['identity_sha256'],
      'activation_sha256':episode.get('activation_sha256'),'endpoint':'before_first_submitted_code_token',
      'positions':{},'scope':'predict eventual external interference; not inferred mental commitment'}
    if text!=episode['generated_text']:
        return {**result,'unavailable':'tokenizer decode differs from recorded output'}
    start,reason=code_onset(text)
    if reason:return {**result,'unavailable':reason}
    # A token may straddle the boundary; choose the state BEFORE that token.
    previous=''
    for end in range(1,len(ids)+1):
        prefix=decode(ids[:end])
        if not text.startswith(prefix) or not prefix.startswith(previous):
            return {**result,'unavailable':'nonmonotonic or partial-character token decoding before boundary'}
        if len(prefix)>start:
            index=end-1
            result.update(code_char_offset=start,boundary_straddled=len(previous)<start,
              primary_sample_index=index,permitted_generated_prefix_ids=ids[:index])
            for distance in (0,32,64):
                j=index-distance
                result['positions'][str(distance)]={'available':j>=0,'sample_index':j if j>=0 else None,
                  'absolute_residual_token_index':episode['initial_tokens']+j-1 if j>=0 else None}
            return result
        previous=prefix
    return {**result,'unavailable':'code onset beyond recorded tokens'}
