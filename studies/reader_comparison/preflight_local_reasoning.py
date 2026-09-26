"""CPU-only tokenizer and reasoning-setting check; not reader qualification."""
import argparse
import json
from pathlib import Path

from contracts import fingerprint
from literal_evidence import checked_literal_json
from local_text_reader_deliberative import frozen_template
from smoke import digest, write_json


def main():
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    import transformers

    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--jobs', type=Path, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    cfg = json.loads(a.config.read_text())
    if cfg['family'] != 'gptoss' or cfg['reasoning_effort'] != 'medium':
        raise ValueError('Expected registered medium-reasoning GPT-OSS candidate')
    modelpath = snapshot_download(repo_id=cfg['repo'], revision=cfg['revision'],
                                  local_files_only=True,
                                  allow_patterns=['*.json', '*.jinja', '*.txt'])
    tok = AutoTokenizer.from_pretrained(modelpath)
    template = frozen_template(tok.get_chat_template(), cfg['family'], cfg['chat_template_date'])
    kwargs = dict(chat_template=template, tokenize=False, add_generation_prompt=True,
                  enable_thinking=False)
    synthetic = [{'role': 'user', 'content': 'Return an empty JSON object.'}]
    low = tok.apply_chat_template(synthetic, reasoning_effort='low', **kwargs)
    medium = tok.apply_chat_template(synthetic, reasoning_effort=cfg['reasoning_effort'], **kwargs)
    if 'Reasoning: medium' not in medium or 'Reasoning: low' not in low or medium == low:
        raise ValueError('Reasoning setting is not reflected in the actual chat template')
    checked = 0
    for path in a.jobs:
        for job in json.loads(path.read_text())['jobs']:
            if job['request_id'] != fingerprint({'system': job['system'], 'evidence': job['evidence']}):
                raise ValueError('Changed request identity')
            data = checked_literal_json(job['evidence'], tok)
            if json.loads(data) != job['evidence']:
                raise ValueError('Changed evidence values')
            checked += 1
    report = {'passed': True, 'requests_checked': checked,
              'scope': 'CPU tokenizer/encoding check only; no model generation or quality qualification.',
              'reasoning_setting_rendered': 'medium', 'low_medium_templates_differ': True,
              'escaped_payloads_with_registered_special_ids': 0, 'roundtrip_values_preserved': True,
              'config': cfg, 'transformers': transformers.__version__,
              'chat_template_sha256': fingerprint(template),
              'source_hashes': {str(path): digest(path) for path in
                               [a.config, *a.jobs, Path(__file__),
                                Path(__file__).with_name('local_text_reader_deliberative.py'),
                                Path(__file__).with_name('literal_evidence.py')]}}
    write_json(a.out, report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
