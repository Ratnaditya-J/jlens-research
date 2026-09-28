"""Read-only localhost dashboard. Only allowlisted artifacts and aggregate status are public."""
import argparse, datetime, json, mimetypes, shutil, threading, time, re, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUN=ROOT/'runs/reader-comparison'
EVIDENCE=ROOT/'studies/reader_comparison/evidence'
_cache={}
_snapshot_lock=threading.Lock()
_read_errors=set()
def read(path):
    try:
        stamp=path.stat().st_mtime_ns
        if path not in _cache or _cache[path][0]!=stamp:
            _cache[path]=(stamp,json.loads(path.read_text()))
        _read_errors.discard(str(path))
        return _cache[path][1]
    except (OSError,ValueError):
        _read_errors.add(str(path))
        if path in _cache:return _cache[path][1]
        return {}
def status():
    pipeline=read(RUN/'legacy-remaining-pipeline/status.json')
    progress=read(RUN/'legacy-remaining-reviews/progress.json')
    reg=read(RUN/'legacy-remaining-reviews/registration.json')
    budget=read(ROOT.parent/'reader-runtime/openrouter-budget.json')
    if not all(k in budget for k in ['spent_microusd','reserved_microusd','additional_limit_usd']):raise RuntimeError('Budget aggregate unavailable')
    process_text=subprocess.run(['ps','-axo','command'],capture_output=True,text=True,check=True).stdout
    pipeline_alive=any('/run_legacy_remaining_pipeline.py' in line and 'python' in line.lower() for line in process_text.splitlines())
    reviewed=(RUN/'legacy-remaining-reviews/complete.json').exists()
    audited=(EVIDENCE/'legacy-remaining-review-audit.json').exists() and (RUN/'legacy-remaining-pipeline/complete.json').exists()
    final=read(HERE/'final-integration.json') if (HERE/'final-integration.json').is_file() else {}
    integrated=bool(audited and final.get('verified_complete') is True and final.get('verification_artifact') and (ROOT/final['verification_artifact']).is_file())
    rows=[
      ('Subject and behavior evidence','Exact checkpoint identities, captured episodes and independent behavioral labels.','complete','Foundation'),
      ('Checkpoint-specific J-lens and probes','Lens fit and independently trained raw-activation / transformed-activation probes.','complete','Foundation'),
      ('Oracle verbalizer and captured readouts','Same-subject Qwen activations with the published reader component; not full reconstruction.','complete','Qwen comparison'),
      ('Reader qualification and calibration','Accepted judges, coverage gates and frozen endpoint thresholds.','complete','Qwen comparison'),
      ('Six held-out endpoint evaluations','Before, during and after action; end of prompt; earlier −32 / −64 offsets.','complete','Qwen comparison'),
      ('Disagreement and fidelity assessment','Shared-prefix confounds, context/shuffle controls and bounded four-case Oracle audit.','complete','Qwen comparison'),
      ('Original GPT-OSS baseline analysis','Existing before-action J-view, summary and activation-probe results preserved.','complete','GPT-OSS extension'),
      ('Benign specificity panels','47 authorization/debugging and 24 monitor-maintenance cases evaluated and audited.','complete','GPT-OSS extension'),
      ('Template summaries','472 unique summaries complete; all receipts verified.','complete','GPT-OSS extension'),
      ('Remaining template and code-onset reviews','4,068 new requests plus exact cache reuse; original partial results remain preserved.','complete' if reviewed else 'in_progress','GPT-OSS extension'),
      ('Remaining evaluation and receipt audit','Frozen two-panel evaluation, source hashes, unavailable responses and receipt checks.','complete' if audited else ('in_progress' if reviewed else 'pending'),'Closeout'),
      ('Final integrated report and evidence','Add remaining findings, reconcile uncertainty, visually verify the editable report and package evidence.','complete' if integrated else ('in_progress' if audited else 'pending'),'Closeout')]
    counts={s:sum(x[2]==s for x in rows) for s in ['complete','in_progress','pending']}
    failed=pipeline.get('state')=='failed' or progress.get('dispatch_stopped',False) or (pipeline.get('state')=='running' and not pipeline_alive)
    current='Final report and evidence integration' if audited else ('Evaluation and receipt verification' if reviewed else 'Template + code-onset API reviews')
    if integrated:current='Registered execution and final integration verified'
    if failed:current='Review pipeline needs recovery'
    spent=budget.get('spent_microusd',0)/1e6; reserved=budget.get('reserved_microusd',0)/1e6; limit=budget.get('additional_limit_usd',80)
    missing=len(progress.get('missing',{})); old=len(reg.get('previously_missing',{})); cached=len(reg.get('cached',{}))
    at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    return dict(updated_at=at,project_complete=integrated,counts=counts,total=len(rows),current=current,attention=failed,
      data_stale=bool(_read_errors),source_read_errors=len(_read_errors),pipeline_alive=pipeline_alive,progress_age_seconds=round(time.time()-(RUN/'legacy-remaining-reviews/progress.json').stat().st_mtime) if progress else None,pipeline_state=pipeline.get('state','unknown'),pipeline_stage=pipeline.get('stage',''),milestones=[dict(id=i+1,title=r[0],detail=r[1],state=r[2],stream=r[3]) for i,r in enumerate(rows)],
      reviews=dict(attempted=progress.get('attempted',0),total=progress.get('total',4068),cached=cached,new_usable=max(0,progress.get('usable',cached)-cached),new_unavailable=max(0,missing-old),prior_unavailable=old,concurrency=reg.get('concurrency',8),updated_at=datetime.datetime.fromtimestamp((RUN/'legacy-remaining-reviews/progress.json').stat().st_mtime,datetime.timezone.utc).isoformat() if progress else None),
      budget=dict(limit=limit,settled=spent,reserved=reserved,available=max(0,limit-spent-reserved),known_prior_uncertain=1.058460,scope='Cumulative additional OpenRouter only; excludes earlier project spend and GPU/storage costs.'),
      artifacts=dict(report='13-page verified snapshot before remaining cohorts',evidence='16,241 verified files; dated snapshot, not full regeneration bundle'))
def save_snapshot():
    with _snapshot_lock:
        d=status(); temp=HERE/'status.json.tmp'; temp.write_text(json.dumps(d,indent=2)+'\n');temp.replace(HERE/'status.json');return d
FILES={'/':HERE/'index.html','/index.html':HERE/'index.html','/technical-record.docx':ROOT/'reports/reader-comparison/technical-record.docx','/technical-record.md':ROOT/'reports/reader-comparison/technical-record.md','/qwen-results.md':ROOT/'reports/reader-comparison/four-endpoint-heldout-results.md','/legacy-controls.md':ROOT/'reports/reader-comparison/legacy-specificity-results.md','/oracle-audit.md':ROOT/'reports/reader-comparison/oracle-temporal-fidelity-audit.md','/evidence-verification.json':EVIDENCE/'comparison-controls-package-verification.json','/evidence.tar.gz':ROOT.parent/'reader-runtime/comparison-and-controls-evidence-package/comparison-and-controls-evidence.tar.gz'}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path=self.path.split('?',1)[0]
        if path=='/status.json':
            try:data=json.dumps(save_snapshot()).encode()
            except Exception:
                self.send_error(503,'Status temporarily unavailable');return
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        p=FILES.get(path)
        if p is None or not p.is_file():self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(p.name)[0] or 'application/octet-stream');self.send_header('Content-Length',str(p.stat().st_size));self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
        with p.open('rb') as f:shutil.copyfileobj(f,self.wfile)
    def log_message(self,*args):pass
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);p.add_argument('--snapshot',action='store_true');a=p.parse_args();snapshot=save_snapshot()
    if a.snapshot:
        page=HERE/'index.html';text=page.read_text();payload=json.dumps(snapshot).replace('<','\\u003c');text=re.sub(r'/\* SNAPSHOT_START \*/.*?/\* SNAPSHOT_END \*/',lambda m:'/* SNAPSHOT_START */\ndraw('+payload+');\n/* SNAPSHOT_END */',text,flags=re.S);page.write_text(text)
    if not a.snapshot:
        print(f'J-lens dashboard: http://127.0.0.1:{a.port}',flush=True)
        ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
