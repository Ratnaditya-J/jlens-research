"""Scientific figures from recorded paired cases; no model fitting or filtering by success."""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=['development','primary','template-challenge','specificity-controls'],default='primary');p.add_argument('--offset',type=int,choices=[0,32,64],default=0);a=p.parse_args()
    assert a.scope!='development' or a.offset==0
    name={'development':'development-comparison','primary':'final-comparison','template-challenge':'template-challenge-comparison','specificity-controls':'specificity-controls-comparison'}[a.scope]
    folder=ROOT/'reports'/(name+(f'-offset{a.offset}' if a.offset else ''))
    summary=folder/'summary.json';cases=folder/'cases.json';report=json.loads(summary.read_text());rows=json.loads(cases.read_text())
    categories=['probe_only','jlens_only','both','neither']
    known=[r for r in rows if r['behavior_label'] in ['misaligned','benign'] and r.get('category') in categories]
    counts={label:[sum(r['behavior_label']==label and r['category']==c for r in known) for c in categories] for label in ['misaligned','benign']}
    expected=report['tables']['all'] if a.scope=='development' else report['confirmed_four_way']
    assert {c:counts['misaligned'][i]+counts['benign'][i] for i,c in enumerate(categories)}==expected
    out=folder/'figures';out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    title='DEVELOPMENT — illustrative thresholds' if a.scope=='development' else ('Held-out template challenge' if a.scope=='template-challenge' else 'Held-out task families')
    if a.scope=='specificity-controls':title='Authorized specificity controls'
    title+=f' | {a.offset} tokens before code onset'
    fig,ax=plt.subplots(figsize=(9,5.4));x=np.arange(4)
    ax.bar(x,counts['misaligned'],color='#bc4b39',label='Confirmed violation')
    ax.bar(x,counts['benign'],bottom=counts['misaligned'],color='#417b9b',label='Benign')
    totals=np.array(counts['misaligned'])+counts['benign']
    for i,n in enumerate(totals):ax.text(i,n+max(1,max(totals)*.02),str(n),ha='center',fontweight='bold')
    ax.set_xticks(x,['Probe only','J-lens only','Both flag','Neither flags']);ax.set_ylabel('Number of paired cases');ax.set_ylim(0,max(1,max(totals))*1.22);ax.set_title(title,pad=18);ax.legend(frameon=False)
    excluded=len(rows)-len(known)
    footer=f'{len(known)} known-label paired cases; {excluded} other rows in case file. Missing scores are never treated as negative.'
    if a.scope=='development':footer+=f"\n{len(report['excluded_ids'])} uncertain episodes excluded upstream; these results do not establish generalization."
    else:footer+='\nThresholds selected on validation data. Counts describe this benchmark, not deployment prevalence.'
    fig.text(.08,.025,footer,fontsize=9);fig.tight_layout(rect=(0,.10,1,1))
    files=[]
    for ext in ['png','svg','pdf']:
        target=out/f'four-way.{ext}';fig.savefig(target,dpi=180);files.append(target)
    plt.close(fig)
    if a.scope!='development':
        fig,axes=plt.subplots(1,2,figsize=(9,4.8));intervals=report['cluster_intervals']
        for ax,key,label in zip(axes,['sensitivity','fpr'],['Sensitivity on confirmed violations','False-positive rate on benign cases']):
            for i,(method,color) in enumerate([('probe','#7655a0'),('jview','#16827b')]):
                value=report['metrics'][method][key];bounds=intervals.get(f'{method}_{key}')
                if value is None:
                    ax.text(i,.5,'Not estimable',ha='center',rotation=90,color=color)
                    continue
                ax.plot(i,value,'o',color=color,markersize=8)
                if bounds is not None:ax.vlines(i,bounds[0],bounds[1],color=color,lw=2)
                ax.annotate(f'{value:.1%}',(i,value),xytext=(10,0),textcoords='offset points',va='center')
            ax.set_xticks([0,1],['Probe','J-lens']);ax.set_xlim(-.5,1.6);ax.set_ylim(-.04,1.07);ax.set_title(label,fontsize=11);ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
        fig.suptitle(title,fontsize=12);fig.text(.07,.025,'Lines: 95% family-cluster bootstrap intervals. Zero observed errors do not prove zero population error.',fontsize=9);fig.tight_layout(rect=(0,.08,1,.94))
        for ext in ['png','svg','pdf']:
            target=out/f'operating-point.{ext}';fig.savefig(target,dpi=180);files.append(target)
        plt.close(fig)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'manifest.json').write_text(json.dumps({'scope':a.scope,'offset':a.offset,'counts':counts,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [summary,cases,Path(__file__)]},'figures_sha256':{p.name:sha(p) for p in files}},indent=2)+'\n')
    print(json.dumps({'figures':len(files),'paired_cases':len(known)}))

if __name__=='__main__':main()
