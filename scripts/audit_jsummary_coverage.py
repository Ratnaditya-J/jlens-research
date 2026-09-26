"""Separate upstream endpoint coverage from downstream summarizer/reviewer loss."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'studies/reader_comparison'))
from smoke import write_json,digest
def main():
 p=argparse.ArgumentParser();p.add_argument('--offset',type=int,default=0);p.add_argument('--dataset',default='fresh');a=p.parse_args();stem=a.dataset+(f'-offset{a.offset}' if a.offset else '');data=ROOT/f'runs/{stem}-assembled';summ=ROOT/f'runs/{stem}-jsummary-test';out=ROOT/f'reports/jsummary-{stem}'
 paths=[data/'test-records.json',data/'test-readouts.json',summ/'summaries.json',summ/'scores.json'];records,readouts,summaries,scores=[json.loads(p.read_text()) for p in paths];ro={r['episode_id']:r for r in readouts};ss={};scores={r['episode_id']:r for r in scores}
 for r in summaries:ss.setdefault(r['episode_id'],set()).add(r['layer'])
 arms=['jsummary','jsummary_plus_tokens','jsummary_blind','jview_blind','jsummary_shuffled'];report={'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in paths},'panels':{},'scope':'Descriptive stored-artifact coverage. No feature at an endpoint is distinct from a summary or review failure. This audit does not infer the original upstream reason for every missing feature.'}
 for name,rows in [('all',records),('known',[r for r in records if r['label'] in ['benign','misaligned']]),('positive',[r for r in records if r['label']=='misaligned']),('benign',[r for r in records if r['label']=='benign'])]:
  ids={r['episode_id'] for r in rows};has_features={r['episode_id'] for r in rows if r.get('feature_index') is not None};has_readouts=ids&set(ro);complete_summary={eid for eid in has_readouts if {l['layer'] for l in ro[eid]['layers']}<=ss.get(eid,set())}
  panel={'requested':len(ids),'stored_feature':len(has_features),'stored_readout':len(has_readouts),'no_stored_readout':len(ids-has_readouts),'complete_summary_among_readouts':len(complete_summary),'incomplete_summary_among_readouts':len(has_readouts-complete_summary),'arms':{}}
  for arm in arms:
   available={eid for eid in ids if scores.get(eid,{}).get(arm,{}).get('score') is not None};panel['arms'][arm]={'available':len(available),'missing_with_stored_readout':len(has_readouts-available),'available_without_stored_readout':len(available-has_readouts)}
  report['panels'][name]=panel
 out.mkdir(parents=True,exist_ok=True);write_json(out/'coverage.json',report);print(json.dumps(report['panels']['known']))
if __name__=='__main__':main()
