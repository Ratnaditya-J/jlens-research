"""Recount control results under original and authorization-aware labels."""
import hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    folder=ROOT/'runs/specificity-controls'
    original=folder/'review-summary.json';derived=folder/'review-summary-authorized.json'
    cases=ROOT/'reports/specificity-controls-comparison/cases.json'
    summary=cases.with_name('summary.json');marker=ROOT/'runs/controller/specificity-scoring-complete.json'
    assert sha(summary)==json.loads(marker.read_text())['summary_sha256']
    old=json.loads(original.read_text());new=json.loads(derived.read_text())
    assert sha(original)==new['source_summary_sha256']
    originals={r['episode_id']:r for r in old['rows']};labels={r['episode_id']:r for r in new['rows']}
    data=json.loads(cases.read_text());assert set(originals)==set(labels)=={r['episode_id'] for r in data}
    for eid,row in labels.items():
        assert row['original_label']==originals[eid].get('label')
        for name,digest in row['review_sha256'].items():assert sha(folder/eid/name)==digest
        if row['authorized_benign_consensus_retained']:
            judgments=[json.loads((folder/eid/name).read_text())['judgment'] for name in row['review_sha256']]
            assert len(judgments)==2 and all(j['label']=='benign' and j['confidence']=='high' for j in judgments)
    groups={}
    for name,select in [('original_benign',lambda r:originals[r['episode_id']].get('label')=='benign'),('authorization_amended_benign',lambda r:labels[r['episode_id']]['authorized_benign_consensus_retained']),('all_derived_benign',lambda r:labels[r['episode_id']]['label']=='benign')]:
        selected=[r for r in data if select(r)]
        paired=[r for r in selected if r['probe_flag'] is not None and r['jlens_flag'] is not None]
        groups[name]={'n':len(selected),'paired_n':len(paired),'missing_paired':len(selected)-len(paired),'four_way':{k:sum(r['category']==k for r in paired) for k in ['probe_only','jlens_only','both','neither']},'probe_fp':sum(r['probe_flag'] for r in paired),'jview_fp':sum(r['jlens_flag'] for r in paired),'episode_ids':[r['episode_id'] for r in paired]}
    out={'groups':groups,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [original,derived,cases,summary,Path(__file__)]},'scope':'Secondary robustness check; original primary labels and frozen detector thresholds are unchanged. Authorization aggregation was amended after behavior review and before control detector scoring. Four synthetic control families do not estimate deployment specificity.'}
    dest=cases.with_name('label-policy-sensitivity.json');dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:{x:v[x] for x in ['n','paired_n','probe_fp','jview_fp']} for k,v in groups.items()}))
if __name__=='__main__':main()
