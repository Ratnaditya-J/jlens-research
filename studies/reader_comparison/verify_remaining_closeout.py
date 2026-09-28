"""Read-only preservation preflight and terminal evidence gate. Never dispatches calls."""
import argparse,json
from pathlib import Path
from smoke import digest,write_json
ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'studies/reader_comparison/evidence'
def verify(require_terminal=False):
 launch=json.loads((EVIDENCE/'legacy-remaining-launch.json').read_text());sources={}
 for path,expected in launch['source_hashes'].items():
  if digest(path)!=expected:raise ValueError('Original or copied input changed: '+path)
  sources[path]=expected
 for alias,original in [('runs/fresh-completion-assembled','runs/fresh-assembled'),('reports/fresh-completion-comparison','reports/final-comparison')]:
  if (ROOT/alias).resolve()!=(ROOT/original).resolve():raise ValueError('Input alias changed')
 original=json.loads((ROOT/'runs/fresh-jsummary-test/review-manifest.json').read_text())
 prepared=json.loads((ROOT/'runs/reader-comparison/legacy-remaining-review-preparation/fresh-completion.json').read_text())
 if original!=prepared['manifest']:raise ValueError('Original review payload provenance changed')
 for endpoint in ['before_action','end_prompt','before_action_32','before_action_64','during_action','after_action']:
  prefix='standard' if endpoint in ['during_action','after_action'] else 'accepted'
  folder=ROOT/f'runs/reader-comparison/{prefix}-evaluation-{endpoint}'
  for name in ['summary.json','cases.json']:sources[str(folder/name)]=digest(folder/name)
 b=json.loads((ROOT.parent/'reader-runtime/openrouter-budget.json').read_text())
 if b['spent_microusd']+b['reserved_microusd']>int(b['additional_limit_usd']*1e6):raise ValueError('Budget plus reserved charges exceeds authorization')
 terminal=[ROOT/'runs/reader-comparison/legacy-remaining-pipeline/complete.json',ROOT/'runs/reader-comparison/legacy-remaining-reviews/complete.json',EVIDENCE/'legacy-remaining-review-audit.json',EVIDENCE/'legacy-remaining-summary-audit.json']
 missing=[str(p.relative_to(ROOT)) for p in terminal if not p.exists()]
 if require_terminal and missing:raise ValueError('Cannot close out before terminal evidence: '+', '.join(missing))
 if not missing:
  for auditpath in terminal[2:]:
   audit=json.loads(auditpath.read_text())
   for path,expected in audit['source_hashes'].items():
    if digest(path)!=expected:raise ValueError('Audited dependency changed: '+path)
    sources[path]=expected
  for path in terminal:sources[str(path)]=digest(path)
  for panel in ['template-challenge','fresh-completion']:
   for name in ['summary.json','cases.json']:
    path=ROOT/f'reports/jsummary-{panel}'/name;sources[str(path)]=digest(path)
 return {'original_partial_outputs_preserved':True,'input_alias_and_review_manifest_equal':True,'terminal_evidence_complete':not missing,'missing_terminal_evidence':missing,'source_hashes':sources,'budget_snapshot':{k:b[k] for k in ['additional_limit_usd','spent_microusd','reserved_microusd']},'scope':'Preservation and evidence gate only. A final scientific synthesis, visually verified updated document and verified final package remain required; this gate does not declare full initiative completion.'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--require-terminal',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('Preserve existing verification record')
 d=verify(a.require_terminal);write_json(a.out,d);print(json.dumps({k:d[k] for k in ['original_partial_outputs_preserved','input_alias_and_review_manifest_equal','terminal_evidence_complete','missing_terminal_evidence']}))
if __name__=='__main__':main()
