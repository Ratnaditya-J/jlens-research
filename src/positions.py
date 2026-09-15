"""Outcome- and detector-blind alignment of submitted code to saved causal states."""
from src.source_parser import extract_code_and_files

def code_onset(text):
    code,extra=extract_code_and_files(text)
    if extra:return None,'multiple-file action unsupported'
    if not code:return None,'empty code'
    # Restrict primary alignment to an unambiguous structured submission.
    if '```' not in text and '<file' not in text:return None,'unstructured submission'
    start=text.find(code)
    if start<0 or text.find(code,start+1)>=0:return None,'code substring not unique'
    return start,None

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
