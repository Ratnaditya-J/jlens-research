"""Consolidate completed four-way results without pooling different cohorts."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
panels=[('Primary, code onset','final-comparison'),('Separately calibrated, 32 tokens earlier','final-comparison-offset32'),('Separately calibrated, 64 tokens earlier','final-comparison-offset64'),('Unseen wording challenge','template-challenge-comparison'),('Authorized fixtures/debugging','specificity-controls-comparison'),('Authorized monitor maintenance','monitor-controls-comparison')]
keys=['probe_only','jlens_only','both','neither'];rows=[];inputs={};pending=[]
for title,folder in panels:
 p=ROOT/'reports'/folder/'summary.json'
 if not p.exists():pending.append(title);continue
 inputs[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();d=json.loads(p.read_text());t=d['tables'];counts={k:sum(t[label]['counts'][k] for label in ['misaligned','benign']) for k in keys};n=sum(counts.values());assert n==d['confirmed_paired_n']
 for label,table in [('All known labels',{'denominator':n,'counts':counts}),('Confirmed violations',t['misaligned']),('Benign',t['benign'])]:
  assert sum(table['counts'].values())==table['denominator'];rows.append({'evaluation':title,'stratum':label,'n':table['denominator'],**table['counts']})
report={'scope':'Separate evaluation panels, known labels with paired scores only; no pooled totals. Earlier endpoints can reuse primary episodes and have different available populations.','rows':rows,'source_sha256':inputs,'pending_panels':pending}
(ROOT/'reports/coverage-overview.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['# Four-category coverage across completed evaluations','',report['scope'],'','| Evaluation | Cases | N | Probe only | J-lens only | Both | Neither |','|---|---|---:|---:|---:|---:|---:|']
for r in rows:lines.append('| '+r['evaluation']+' | '+r['stratum']+' | '+' | '.join(str(r[k]) for k in ['n',*keys])+' |')
lines+=['','“Only” describes which detector flags. On benign cases, flags are false positives; on confirmed violations, neither means both miss. Unknown labels and missing scores are excluded here and remain in each panel’s full report.','', 'J-lens flags include ambiguous rubric scores under the frozen threshold. Earlier endpoint rows use their own training and validation; do not confuse them with transfer of the unchanged onset detector. Eight provider refusals remain unavailable at the 64-token endpoint.']
if pending:lines+=['','Still pending: '+', '.join(pending)+'.']
(ROOT/'reports/coverage-overview.md').write_text('\n'.join(lines)+'\n');print('Built',len(rows),'rows;',len(pending),'pending panel')
