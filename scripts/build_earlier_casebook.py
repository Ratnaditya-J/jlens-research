"""Build a self-contained inspection artifact from frozen joined results."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', choices=['development','final'], required=True)
    parser.add_argument('--offset',type=int,choices=[32,64],required=True)
    args = parser.parse_args()
    assert args.scope=='final'
    stem=f'fresh-offset{args.offset}'
    final = args.scope == 'final'
    reportdir = ROOT / ('reports/final-comparison' if final else 'reports/development-comparison')
    reportdir=ROOT/f'reports/final-comparison-offset{args.offset}'
    summary = read(reportdir / 'summary.json')
    cases = read(reportdir / 'cases.json')
    if final:
        selected = summary['casebook_ids']
        contexts = {r['episode_id']:r for r in read(ROOT/f'runs/{stem}-assembled/test-contexts.json')['rows']}
        views = {r['episode_id']:r for r in read(ROOT/f'runs/{stem}-assembled/test-readouts.json')}
        behavior = ROOT/'runs/fresh'
        review = ROOT/f'runs/{stem}-jview-test/reviews'
    else:
        selected = []
        for label in ['misaligned','benign']:
            for category in ['probe_only','jlens_only','both','neither']:
                ids = [r['episode_id'] for r in cases if r['behavior_label']==label and r['category']==category]
                selected.extend(sorted(ids,key=lambda s:hashlib.sha256(s.encode()).hexdigest())[:3])
        contexts = {r['episode_id']:r for r in read(ROOT/'runs/development-permitted-text.json')['rows']}
        views = {r['episode_id']:r for r in read(ROOT/'runs/jviews32/readouts.json')}
        behavior = ROOT/'runs/confirmation'
        review = ROOT/'runs/jview-interpretation-v1/reviews'
    lookup = {r['episode_id']:r for r in cases}
    entries = []
    sources = {str(p.relative_to(ROOT)):sha(p) for p in [reportdir/'summary.json',reportdir/'cases.json']}
    for eid in selected:
        directory = behavior/eid
        evidence = {}
        for name in ['external-audit.json','adjudication-v2.json']:
            path = directory/name
            if path.exists():
                evidence[name] = read(path)
                sources[str(path.relative_to(ROOT))] = sha(path)
        judgments = []
        for path in sorted((review/eid).glob('*.json')):
            item = read(path)
            judgments.append({k:item.get(k) for k in ['arm','resolved_model','judgment','elapsed_seconds','transport']})
            if item.get('transport'):judgments[-1]['resolved_model']+=' via '+item['transport']['gateway']
            sources[str(path.relative_to(ROOT))] = sha(path)
        entries.append({'case':lookup[eid],'context':contexts[eid],'view':views[eid],
                        'judgments':judgments,'external_evidence':evidence})
    payload = {'scope':args.scope,'summary':summary,'entries':entries,
               'selection':'Up to three lowest SHA256 episode IDs per category and independent label; empty categories have no invented examples',
               'source_sha256':sources}
    for path in [Path(__file__), ROOT/'scripts/casebook-template.html', ROOT/(f'runs/{stem}-assembled/test-contexts.json' if final else 'runs/development-permitted-text.json'), ROOT/(f'runs/{stem}-assembled/test-readouts.json' if final else 'runs/jviews32/readouts.json')]:
        sources[str(path.relative_to(ROOT))] = sha(path)
    template = (ROOT/'scripts/casebook-template.html').read_text()
    encoded = json.dumps(payload, ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    out = reportdir/'casebook.html'
    out.write_text(template.replace('__PAYLOAD__',encoded))
    (reportdir/'casebook-manifest.json').write_text(json.dumps({'scope':args.scope,'case_ids':selected,'html_sha256':sha(out),'source_sha256':sources},indent=2)+'\n')
    print(json.dumps({'path':str(out),'cases':len(entries),'scope':args.scope}))

if __name__ == '__main__': main()
