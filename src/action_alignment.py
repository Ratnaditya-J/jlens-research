"""Retrospective source-line alignment; never selects detector thresholds."""
from src.positions import code_onset
from src.source_parser import extract_code_and_files


def align_actions(episode, trace, decode):
    result = {'episode_id': episode['episode_id'], 'actions': [],
              'scope': 'Generated-token distance to exercised source lines; not mental commitment or elapsed execution time'}
    if not trace['observables_match_original_audit']:
        return {**result, 'unavailable': 'traced behavior differs from original audit'}
    ids = episode['generated_token_ids']
    text = decode(ids)
    if text != episode['generated_text']:
        return {**result, 'unavailable': 'tokenizer decode differs from recorded output'}
    start, reason = code_onset(text)
    if reason:
        return {**result, 'unavailable': reason}
    code, _ = extract_code_and_files(text.split('<|channel|>final<|message|>', 1)[-1])
    lines = code.splitlines(keepends=True)
    boundaries = []
    for line in trace['candidate_executed_source_lines']:
        if not 1 <= line <= len(lines):
            return {**result, 'unavailable': 'traced source line out of bounds'}
        # First non-whitespace character, not indentation on the statement line.
        offset = start + sum(map(len, lines[:line-1]))
        offset += len(lines[line-1]) - len(lines[line-1].lstrip())
        boundaries.append((line, offset))
    previous = ''
    for end in range(1, len(ids)+1):
        prefix = decode(ids[:end])
        if not text.startswith(prefix) or not prefix.startswith(previous):
            return {**result, 'actions': [], 'unavailable': 'nonmonotonic token decoding'}
        for line, offset in boundaries:
            if len(previous) <= offset < len(prefix):
                result['actions'].append({'source_line': line, 'character_offset': offset,
                    'before_statement_sample_index': end-1,
                    'token_straddles_statement_boundary': len(previous) < offset})
        previous = prefix
        if len(result['actions']) == len(boundaries):
            break
    if len(result['actions']) != len(boundaries):
        return {**result, 'actions': [], 'unavailable': 'statement beyond decoded tokens'}
    return result
