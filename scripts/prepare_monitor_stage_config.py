"""Freeze a CPU-only reconstruction plan after monitor scoring completes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
cal=ROOT/'runs/fresh-calibration';lockp=cal/'lock.json';lock=json.loads(lockp.read_text());data=ROOT/'runs/monitor-controls-assembled';mp=data/'manifest.json';assembled=json.loads(mp.read_text());jd=ROOT/'runs/monitor-controls-jview-test';complete=json.loads((jd/'complete.json').read_text());assert not complete['errors'],'Resolve unavailable judgments explicitly before reproduction'
inputs=set(lock['source_hashes'])|{str(lockp.relative_to(ROOT)),str(mp.relative_to(ROOT)),'configs/identity-fp32.json','scripts/paired_breakdown.py','src/comparison_diagnostics.py','scripts/evaluate_monitor_controls.py'}
inputs.update(str((cal/n).relative_to(ROOT)) for n in lock['artifacts']);inputs.update(str((data/n).relative_to(ROOT)) for n in assembled['files_sha256']);inputs.update(str((jd/n).relative_to(ROOT)) for n in ['scores.json','complete.json'])
cfg={'stage':'compare','identity_config':'configs/identity-fp32.json','inputs_sha256':{n:sha(ROOT/n) for n in sorted(inputs)},'commands':[{'script':'evaluate_monitor_controls.py','args':[]}],'outputs':[f'reports/monitor-controls-comparison/{n}' for n in ['summary.json','cases.json','cases.csv']],'resource_estimate':{'gpu_hours':0,'api_calls':0,'basis':'Reconstruct frozen monitor tables from saved scores'},'scope':'Original primary calibration unchanged; no API calls or label changes; secondary monitor control panel only'}
p=ROOT/'configs/stages/compare-monitor-controls.json';text=json.dumps(cfg,indent=2)+'\n'
if p.exists():assert p.read_text()==text
else:p.write_text(text)
print(p.relative_to(ROOT))
