"""Materialize the deterministic disagreement selections with source evidence."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'studies/reader_comparison'))
from smoke import digest,write_json

def main():
 p=argparse.ArgumentParser();p.add_argument('--offset',type=int,default=0);p.add_argument('--dataset',default='fresh');a=p.parse_args();stem=a.dataset+(f'-offset{a.offset}' if a.offset else '');report=ROOT/f'reports/jsummary-{stem}';data=ROOT/f'runs/{stem}-assembled';summ=ROOT/f'runs/{stem}-jsummary-test'
 paths=[report/'summary.json',report/'cases.json',data/'test-contexts.json',data/'test-readouts.json',summ/'summaries.json',summ/'scores.json']
 summary,cases,contexts,readouts,summaries,scores=[json.loads(p.read_text()) for p in paths]
 cases={r['episode_id']:r for r in cases};contexts={r['episode_id']:r for r in contexts['rows']};readouts={r['episode_id']:r for r in readouts};scores={r['episode_id']:r for r in scores};by_episode={}
 for row in summaries:by_episode.setdefault(row['episode_id'],[]).append(row)
 evidence=[];lines=[f'# Deterministic disagreement casebook: {stem}','', 'Cases were selected by SHA-256 order within each label/detector-agreement pattern. They illustrate observed outcomes; they do not establish a latent mechanism or causal necessity. Missing methods remain missing. The JSON companion preserves complete causal contexts; the text below reports scores and blind summaries.','']
 for cell in summary['casebook_selection']:
  for eid in cell['ids']:
   row={'episode_id':eid,'pattern':cell['flags'],'outcome_label':cell['label'],'scores':cases[eid]['scores'],'thresholds':summary['thresholds'],'causal_context':contexts.get(eid),'readouts':readouts.get(eid),'summaries':sorted(by_episode.get(eid,[]),key=lambda r:r['layer']),'reviewer_scores':scores.get(eid)};evidence.append(row)
   lines += [f'## {eid}','',f"Outcome label: {cell['label']}; flagged by: {', '.join(cell['flags']) or 'none'}.",'','| Method | Score | Frozen threshold |','|---|---:|---:|']
   for arm,score in row['scores'].items():lines.append(f"| {arm} | {score if score is not None else 'unavailable'} | {summary['thresholds'][arm]:.12g} |")
   lines+=['']
   for s in row['summaries']:lines += [f"Layer {s['layer']} blind summary: {s['interpretation']}",'']
 write_json(report/'casebook-evidence.json',{'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in paths},'cases':evidence});(report/'casebook.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'stem':stem,'cases':len(evidence)}))
if __name__=='__main__':main()
