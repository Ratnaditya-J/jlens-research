"""Align independently traced statements to tokens without loading model weights."""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.action_alignment import align_actions

def main():
    from transformers import AutoTokenizer
    from huggingface_hub import snapshot_download
    p = argparse.ArgumentParser()
    p.add_argument('--episodes', type=Path, required=True)
    p.add_argument('--traces', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    identity = json.loads((ROOT/'configs/identity-fp32.json').read_text())
    base = identity['base']
    location = snapshot_download(base['repo'], revision=base['revision'], local_files_only=True, cache_dir='/workspace/hf-cache')
    tok = AutoTokenizer.from_pretrained(location, trust_remote_code=False)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    rows = []
    for path in sorted(a.traces.glob('*.json')):
        trace = json.loads(path.read_text())
        epfile = a.episodes/trace['episode_id']/'episode.json'
        assert sha(epfile) == trace['provenance']['episode_sha256']
        row = align_actions(json.loads(epfile.read_text()), trace, tok.decode)
        row.update(episode_sha256=sha(epfile), trace_sha256=sha(path))
        rows.append(row)
    report = {'rows': rows, 'total': len(rows),
              'localized': sum(bool(r['actions']) for r in rows),
              'implementation_sha256': {str(f.relative_to(ROOT)):sha(f) for f in [Path(__file__), ROOT/'src/action_alignment.py', ROOT/'src/positions.py', ROOT/'src/source_parser.py']},
              'limitations': ['Retrospective action localization; detector inputs must exclude later tokens', 'No flag trajectory is measured here; token distances alone do not demonstrate early detection', 'Unsupported mechanisms and absent candidates remain unlocalized']}
    content = json.dumps(report, indent=2)+'\n'
    a.output.parent.mkdir(parents=True, exist_ok=True)
    if a.output.exists():
        assert a.output.read_text() == content, 'Changed alignment report'
    else:
        a.output.write_text(content)
    print(json.dumps({'total':report['total'],'localized':report['localized']}))

if __name__ == '__main__': main()
