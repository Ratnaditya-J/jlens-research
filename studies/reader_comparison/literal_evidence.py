"""Render JSON evidence without turning literal delimiters into chat controls."""
import json
import re

_STRING = re.compile(r'"(?:\\.|[^"\\])*"')
_DELIMITERS = {'<':r'\u003c', '>':r'\u003e', '[':r'\u005b', ']':r'\u005d'}


def literal_json(value):
    """Preserve JSON values exactly; escape delimiters only inside strings."""
    raw = json.dumps(value, ensure_ascii=True)
    def escape(match):
        text = match.group(0)
        for character, escaped in _DELIMITERS.items():
            text = text.replace(character, escaped)
        return text
    rendered = _STRING.sub(escape, raw)
    if json.loads(rendered) != value:
        raise ValueError('Evidence encoding changed a JSON value')
    return rendered


def checked_literal_json(value, tokenizer):
    rendered = literal_json(value)
    reserved = set(tokenizer.all_special_ids)
    if reserved.intersection(tokenizer.encode(rendered, add_special_tokens=False)):
        raise ValueError('Reserved control token remains in encoded evidence')
    return rendered
