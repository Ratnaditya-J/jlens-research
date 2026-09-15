"""Self-contained full-token casebook and scientific layer/time diagnostic plots."""
import argparse,hashlib,html,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    from tokenizers import Tokenizer
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');args=p.parse_args()
    source=ROOT/'runs/casebook-full-traces';done=source/'complete.json'
    if args.wait:
        while not done.exists():time.sleep(30)
    complete=json.loads(done.read_text());mp=source/'manifest.json';assert sha(mp)==complete['manifest_sha256'];manifest=json.loads(mp.read_text())
    tokenizer=Tokenizer.from_file(str(ROOT/'runs/cpu-readout/tokenizer.json'))
    output=ROOT/'reports/full-trace-casebook';output.mkdir(parents=True,exist_ok=True);files=[];links=[]
    for eid in manifest['selection']:
        d=source/eid;cp=d/'complete.json';assert sha(cp)==complete['case_complete_sha256'][eid];c=json.loads(cp.read_text())
        for name,digest in c['files_sha256'].items():assert sha(d/name)==digest
        trace=json.loads((d/'trajectory.json').read_text());layers={str(l):json.loads((d/f'layer-{l}.json').read_text()) for l in manifest['layers']};n=len(trace['probe_scores']);onset=trace['primary_sample_index'];action=trace['action'].get('localized_statement_sample_index');x=np.arange(n)-onset
        epfile=ROOT/'runs/fresh'/eid/'episode.json';assert sha(epfile)==trace['episode_sha256'];ep=json.loads(epfile.read_text())
        trace['prompt']='\n'.join(m['role']+': '+m['content'] for m in ep['messages'])
        trace['generated_prefixes']=[tokenizer.decode(trace['generated_token_ids'][:j],skip_special_tokens=False) for j in range(n)]
        # A fixed single-token keyword diagnostic, explicitly distinct from J rubric scores.
        token=next(int(k) for k,v in trace['candidate_tokens'].items() if v==' cheat');ci=manifest['candidate_ids'].index(token)
        ranks=np.array([[r['candidate_ranks'][ci] for r in layers[str(l)]] for l in manifest['layers']])
        fig,(ax,bx)=plt.subplots(2,1,figsize=(11,5.6),sharex=True,gridspec_kw={'height_ratios':[1,1.4]})
        ax.plot(x,trace['probe_scores'],color='#7655a0',lw=1.4);lock=json.loads((ROOT/'runs/fresh-calibration/lock.json').read_text());ax.axhline(lock['probe_threshold'],color='#7655a0',ls=':',label='Frozen onset threshold');ax.set_ylim(-.03,1.03);ax.set_ylabel('Probe score');ax.legend(loc='upper right',fontsize=8)
        im=bx.imshow(-np.log10(ranks),origin='lower',aspect='auto',extent=[x[0]-.5,x[-1]+.5,-.5,3.5],vmin=-5.31,vmax=0,cmap='viridis');bx.set_yticks(range(4),manifest['layers']);bx.set_ylabel('Source block');bx.set_xlabel('Generated-token position relative to code onset');fig.colorbar(im,ax=bx,label='−log10 rank of token “ cheat”')
        for a in [ax,bx]:
            a.axvline(0,color='#333333',lw=1,label='Code onset')
            if action is not None:a.axvline(action-onset,color='#b34235',ls='--',lw=1)
        fig.suptitle(eid,fontsize=11);fig.text(.08,.025,'Solid line: code onset. Dashed red: externally localized statement, when available.\nKeyword rank is a display diagnostic, not a J-view detector score. Off-endpoint probe scores are uncalibrated.',fontsize=8);fig.tight_layout(rect=(0,.09,1,.96))
        for ext in ['png','svg','pdf']:
            f=output/f'{eid}.{ext}';fig.savefig(f,dpi=160);files.append(f)
        plt.close(fig)
        payload=json.dumps({'trace':trace,'layers':layers,'candidate_ids':manifest['candidate_ids']},ensure_ascii=True).replace('<','\\u003c')
        page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Full-token J-space casebook</title>
<style>body{font:16px system-ui;margin:32px auto;max-width:1200px;padding:0 20px;color:#17212b}h1{font-size:22px}aside{background:#f0f3f5;padding:14px;line-height:1.5}input{width:80%}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #ddd;padding:5px;text-align:left}pre{white-space:pre-wrap;max-height:220px;overflow:auto;background:#f4f5f6;padding:12px}img{width:100%}code{white-space:pre-wrap}</style>
<h1>CASE_TITLE</h1><aside>Secondary diagnostic on the unchanged held-out casebook. The probe uses its frozen code-onset model and threshold; scores at other positions have not been recalibrated. J token lists and candidate ranks are not J-view flags. Only the independently reviewed sampled positions support rubric-based detection comparisons. Generated text is model output, not evidence of intentions.</aside>
<p><a href="index.html">All cases</a></p><img src="FIGURE" alt="Probe score and four-layer keyword-rank timeline">
<label>Inspect state before generated token <input id="position" type="range" min="0" value="0" step="1"></label><p id="status"></p>
<h2>Assigned task context</h2><pre id="prompt"></pre><h2>Generated prefix available at this state</h2><pre id="prefix"></pre><p>Next generated token: <code id="next"></code></p>
<h2>Fixed top-20 J-space tokens by layer</h2><div id="tokens"></div>
<h2>Full-vocabulary candidate ranks</h2><div id="ranks"></div>
<script type="application/json" id="data">PAYLOAD</script><script>
const d=JSON.parse(document.getElementById('data').textContent),p=document.getElementById('position');p.max=d.trace.probe_scores.length-1;p.value=d.trace.primary_sample_index;
function table(headers,rows){let t=document.createElement('table'),tr=t.insertRow();for(let h of headers){let th=document.createElement('th');th.textContent=h;tr.append(th)}for(let row of rows){let r=t.insertRow();for(let v of row){let c=r.insertCell();c.textContent=v}}return t}
document.getElementById('prompt').textContent=d.trace.prompt;
function draw(){let j=+p.value;document.getElementById('status').textContent=`Sample ${j}; relative to code onset ${j-d.trace.primary_sample_index}; probe score ${d.trace.probe_scores[j].toFixed(5)}; probe flags ${d.trace.probe_flags[j]}.`;
document.getElementById('prefix').textContent=d.trace.generated_prefixes[j];document.getElementById('next').textContent=d.trace.generated_token_text[j];let keys=Object.keys(d.layers);document.getElementById('tokens').replaceChildren(table(['Rank',...keys.map(k=>'Block '+k)],Array.from({length:20},(_,r)=>[r+1,...keys.map(k=>{let t=d.layers[k][j].top_tokens[r];return JSON.stringify(t.text)+'  ('+t.logit.toFixed(3)+')'})])));
document.getElementById('ranks').replaceChildren(table(['Candidate token',...keys.map(k=>'Block '+k)],d.candidate_ids.map((id,i)=>[JSON.stringify(d.trace.candidate_tokens[id]),...keys.map(k=>d.layers[k][j].candidate_ranks[i])])))}p.oninput=draw;draw();</script>'''
        page=page.replace('CASE_TITLE',html.escape(eid)).replace('FIGURE',html.escape(eid+'.png')).replace('PAYLOAD',payload)
        f=output/f'{eid}.html';f.write_text(page);files.append(f);links.append(f'<li><a href="{html.escape(f.name)}">{html.escape(eid)}</a></li>')
    index=output/'index.html';index.write_text('<!doctype html><meta charset="utf-8"><title>Full-token casebook</title><h1>Full-token J-space casebook</h1><p>Prespecified category-by-label case selection. Secondary full-position inspection; no new J-view flags or population timing claims.</p><ul>'+''.join(links)+'</ul>');files.append(index)
    (output/'manifest.json').write_text(json.dumps({'source_complete_sha256':sha(done),'script_sha256':sha(Path(__file__)),'files_sha256':{f.name:sha(f) for f in files},'cases':len(links),'visual_qa':'pending'},indent=2)+'\n');print('rendered',len(links),flush=True)
if __name__=='__main__':main()
