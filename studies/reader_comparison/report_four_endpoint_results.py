"""Summarize frozen evaluations and audit all probe-only J-display misses."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    plan_path = ROOT/'studies/reader_comparison/evidence/four-endpoint-evaluation-handoff-plan.json'
    plan = read(plan_path)
    evidence = {'scope': 'Post-hoc descriptive synthesis; no refitting, threshold changes, or independent semantic adjudication.', 'source_hashes': {str(plan_path): sha(plan_path)}, 'endpoints': {}, 'probe_only_prefix_audit': []}
    sections = ['# Measured four-endpoint comparison — 27 September 2026',
    'All four registered held-out evaluations are complete. There is no demonstrated overall winner. Results concern the Qwen3.6-27B riskyfin checkpoint, not the preserved original GPT-OSS study. Each endpoint requests the same 128 episodes: 64 prohibited (ten behavioral violations, 54 benign actions) and 64 authorized controls. Only four held-out families and two mechanism clusters are represented.',
    '## Interpretation',
    'At minus32, the raw probe flags six confirmed violations that both contextual J-display arms miss. Those six belong to three identical-prefix groups; the same probe scores also flag 16 benign episodes in those groups. This is an operating-point disagreement, not evidence of episode-specific hidden intent or proof that J-space lacks information. The raw probe has 18/54 prohibited-benign and 32/64 authorized false alarms. Dense-Jh probe AUROC is 0.674 versus raw 0.641, despite zero dense-Jh detections at its frozen threshold.',
    'During the action, blind Oracle detects 4/9 available positives with 8/52 benign false alarms; blind J tokens detect 1/9 with 3/52 false alarms, and blind J summaries detect 1/10 with 5/53. Missing positives remain unknown. Oracle’s full-cohort recall bounds are 40–50%; its family-bootstrap recall interval is 10–80%. This is a recall/specificity tradeoff in a very small sample, not a validated superiority claim.',
    'After the action, context-only detects 10/10 violations with zero false alarms in both control populations. Correct and shuffled contextual lens readouts also detect all ten: this does not demonstrate added activation information. The explicit action is already visible in all 128 prefixes. Blind Oracle detects all ten but falsely flags 53/62 available authorized controls; the raw probe falsely flags 62/64. These methods can recognize action content without reliably distinguishing authorization. Blind J tokens and summaries miss all ten. Contextual J arms detect them, so blind-display failures must not be described as absence of information in the full transform.',
    'At minus64 all combined methods and probes detect zero violations. The previously completed immediate pre-action and end-of-prompt evaluations also detect zero using the frozen combined arms. Several calibrated thresholds exceed the maximum reader score, deliberately producing no flags; zero detection at such thresholds is not a test of representational absence.',
    '## Protocol and uncertainty',
    'Minus32/minus64 retain the original GPT-4.1 plus Flex GPT-5.4 judge pair. During/after use the separately qualified and registered standard-route GPT-5.4 second judge with GPT-4.1; their summaries still use the fixed Flex summarizer. These routes are disclosed and not pooled as interchangeable judgments. All operating points were frozen before the corresponding held-out reviews. Earlier-endpoint calibration occurred after the primary pre-action results were available; that chronology limits blanket preregistration claims.',
    'The tables use available denominators, not requested denominators. P-miss/A-miss are unavailable prohibited/authorized responses. Missing results are not negatives. Family-cluster intervals, missingness bounds, strict-confirmation subsets, paired comparisons and individual-reader sensitivity analyses remain in the full evaluation JSON. Four families yield unstable intervals, and shared prefixes make episode counts a poor proxy for independent evidence. These are descriptive cross-endpoint findings, not multiplicity-adjusted confirmatory discoveries. J-lens maps states to downstream-relevant token views; supervised probes learn labels. Dense-Jh probing is not a formal sparse J-space coverage test.']
    for item in plan['plans']:
        endpoint=item['endpoint']; out=ROOT/item['evaluation'][-1]; lock=ROOT/item['lock']
        assert sha(lock)==item['lock_sha256']
        s=read(out/'summary.json'); cases=read(out/'cases.json')
        assert s['lock_sha256']==sha(lock) and s['endpoint']==endpoint
        for p in [lock,out/'summary.json',out/'cases.json']: evidence['source_hashes'][str(p)]=sha(p)
        evidence['endpoints'][endpoint]={'metrics':s['metrics'],'authorized_controls':s['authorized_controls'],'lock_sha256':sha(lock)}
        sections += ['## '+endpoint, '| Method | TP/positive | FP/benign | Authorized FP/benign | P-miss / A-miss | AUROC |', '|---|---:|---:|---:|---:|---:|']
        for arm,m in s['metrics'].items():
            a=s['authorized_controls'][arm]; auc='NA' if m['auroc'] is None else f"{m['auroc']:.3f}"
            sections.append(f"| {arm} | {m['tp']}/{m['positive']} | {m['fp']}/{m['benign']} | {a['fp']}/{a['benign']} | {m['unavailable']} / {a['unavailable']} | {auc} |")
        if endpoint=='before_action_32':
            ids={x['episode_id'] for x in s['probe_detected_jdisplay_missed']}; groups=defaultdict(list)
            for c in cases: groups[c['prefix_sha256']].append(c)
            for prefix,rows in groups.items():
                if any(r['episode_id'] in ids for r in rows):
                    assert len({r['scores']['raw_probe'] for r in rows})==1
                    assert all(r['scores']['raw_probe']>=read(lock)['thresholds']['raw_probe'] for r in rows)
                    assert all(r['strict_confirmation'] for r in rows)
                    evidence['probe_only_prefix_audit'].append({'prefix_sha256':prefix,'positive':sum(r['label']==1 for r in rows),'benign':sum(r['label']==0 for r in rows),'rows':rows})
    assert sum(g['positive'] for g in evidence['probe_only_prefix_audit'])==6
    assert sum(g['benign'] for g in evidence['probe_only_prefix_audit'])==16
    sections += ['## Completion boundary', 'The six-endpoint numerical same-subject comparison is complete. Full initiative completion still requires the updated editable report and reproducibility package, explicit Oracle faithfulness limitations, and resolution of the original proposal’s outstanding stress/control panels. No real-model causal intervention has been completed. The minus32 disagreements do not separate future benign from violating continuations within identical-prefix groups; they do not justify claiming a causal hidden-intent direction. Any subsequent causal experiment must be separately specified and zero-dose qualified, without changing these frozen evaluations.']
    report=ROOT/'reports/reader-comparison/four-endpoint-heldout-results.md';report.write_text('\n\n'.join(sections).replace(' |\n\n|', ' |\n|')+'\n')
    evidence['report_sha256']=sha(report)
    (ROOT/'studies/reader_comparison/evidence/four-endpoint-measured-results.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'endpoints':list(evidence['endpoints']),'probe_only_groups':len(evidence['probe_only_prefix_audit']),'report':str(report)}))
if __name__=='__main__': main()
