"""Read-only project-pod snapshot and deduplicated retained reviewer usage."""
import hashlib,json,re,sys
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from runpod_control import api
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    now=datetime.now(timezone.utc);ids=set();manifests={}
    for p in (ROOT/'runs').glob('pod*.json'):
        s=json.loads(p.read_text());pod=s.get('pod',{});pid=pod.get('id') if isinstance(pod,dict) else None
        if pid:ids.add(pid);manifests[str(p.relative_to(ROOT))]=sha(p)
    pods=[];observed=set()
    for p in api('pods'):
        if p['id'] not in ids:continue
        observed.add(p['id']);row={k:p.get(k) for k in ['id','name','desiredStatus','gpuCount','costPerHr','createdAt','lastStartedAt','lastStatusChange','volumeInGb','containerDiskInGb']}
        try:
            start=datetime.fromisoformat(p['lastStartedAt'].replace(' +0000 UTC','+00:00'));end=now
            if p['desiredStatus']!='RUNNING':
                m=re.search(r'(\w{3} \w{3} \d{1,2} \d{4} \d\d:\d\d:\d\d) GMT',p['lastStatusChange']);assert m
                end=datetime.strptime(m.group(1),'%a %b %d %Y %H:%M:%S').replace(tzinfo=timezone.utc)
            hours=(end-start).total_seconds()/3600;assert hours>=0
            row.update(latest_session_hours=hours,latest_session_gpu_hours=hours*(p.get('gpuCount') or 0),latest_session_rate_times_hours_usd=hours*p['costPerHr'])
        except (ValueError,TypeError,KeyError,AssertionError):row['session_estimate_unavailable']=True
        pods.append(row)
    files=set((ROOT/'runs').glob('**/review*.json'))|set((ROOT/'runs').glob('**/reviews/**/*.json'));seen={};groups=defaultdict(lambda:{'responses':0,'prompt_tokens':0,'completion_tokens':0,'cached_prompt_tokens':0,'reported_cost_usd':0.0,'responses_with_cost':0})
    for path in sorted(files):
        s=json.loads(path.read_text())
        if not isinstance(s,dict) or not s.get('response_id') or not isinstance(s.get('usage'),dict):continue
        rid=s['response_id']
        if rid in seen:continue
        seen[rid]={'path':str(path.relative_to(ROOT)),'sha256':sha(path)}
        group=s.get('transport',{}).get('gateway','direct OpenAI')+' / '+str(s.get('resolved_model','unknown'));g=groups[group];u=s['usage'];g['responses']+=1;g['prompt_tokens']+=u.get('prompt_tokens',0) or 0;g['completion_tokens']+=u.get('completion_tokens',0) or 0;g['cached_prompt_tokens']+=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0) or 0
        if isinstance(u.get('cost'),(int,float)):g['reported_cost_usd']+=u['cost'];g['responses_with_cost']+=1
    for g in groups.values():
        if not g['responses_with_cost']:g['reported_cost_usd']=None
    report={'at':now.isoformat(),'pod_manifest_sha256':manifests,'pods':pods,'manifest_pods_absent_from_current_api':sorted(ids-observed),'running_project_gpus':sum((p.get('gpuCount') or 0) for p in pods if p['desiredStatus']=='RUNNING'),'retained_successful_review_usage':dict(groups),'unique_response_ids':len(seen),'response_sources':seen,'script_sha256':sha(Path(__file__)),'limitations':['Pod estimates cover only the latest provider-reported start/stop interval; they are not lifetime invoices and must not be added to cumulative ledger snapshots.','Stopped-volume storage, terminated-pod history, taxes and other charges are not reconciled here.','Reviewer counts deduplicate response IDs across retained archives; failed/unretained requests, diagnostic pings and this Codex conversation are excluded.','Reported OpenRouter costs are available only where returned in usage; direct-API dollars are not invented from missing billing data.']}
    out=ROOT/'reports/resource-audit.json';out.write_text(json.dumps(report,indent=2)+'\n')
    with (ROOT/'manifests/resource-ledger.jsonl').open('a') as f:f.write(json.dumps({'at':now.isoformat(),'event':'read_only_resource_audit','report_sha256':sha(out),'running_project_gpus':report['running_project_gpus'],'unique_retained_review_responses':len(seen),'scope':'Snapshot, not additive invoice total'})+'\n')
    print(json.dumps({'running_project_gpus':report['running_project_gpus'],'review_responses':len(seen),'groups':dict(groups)}))
if __name__=='__main__':main()
