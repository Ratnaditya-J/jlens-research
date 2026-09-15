"""Descriptive false-positive rates across separate completed evaluation panels."""
import json,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
panels=[('Code onset','final-comparison'),('32 tokens earlier','final-comparison-offset32'),('64 tokens earlier','final-comparison-offset64'),('Unseen wording','template-challenge-comparison'),('Authorized fixtures','specificity-controls-comparison'),('Monitor maintenance','monitor-controls-comparison')]
labels=[];probe=[];jlens=[];counts=[];inputs={}
for title,folder in panels:
 p=ROOT/'reports'/folder/'summary.json';d=json.loads(p.read_text());inputs[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();m=d['metrics'];n=m['probe']['fp']+m['probe']['tn'];assert n==m['jview']['fp']+m['jview']['tn']
 labels.append(title+'\n'+str(n)+' benign cases');probe.append(100*m['probe']['fp']/n);jlens.append(100*m['jview']['fp']/n);counts.append((m['probe']['fp'],m['jview']['fp'],n))
fig,ax=plt.subplots(figsize=(13,6.8));x=np.arange(len(labels));w=.34
for values,offset,color,title,side in [(probe,-w/2,'#3b648d','Activation probe',0),(jlens,w/2,'#ab493f','J-space interpretation',1)]:
 bars=ax.bar(x+offset,values,w,label=title,color=color)
 for b,v,c in zip(bars,values,counts):ax.text(b.get_x()+b.get_width()/2,v+1.8,f'{c[side]}/{c[2]}',ha='center',va='bottom',fontsize=10)
ax.set_ylim(0,112);ax.set_yticks([0,20,40,60,80,100]);ax.set_ylabel('False-positive rate (%)');ax.set_xticks(x,labels,fontsize=10);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False);ax.legend(loc='upper left',frameon=False)
fig.suptitle('Probe specificity breaks on authorized actions',fontsize=18,y=.97)
fig.text(.09,.045,'Separate evaluation panels; do not pool counts. Earlier endpoints use their own calibration.\nBars describe observed cases, not deployment rates. Few task families and zero observed errors limit generalization.',fontsize=10)
fig.subplots_adjust(left=.09,right=.98,bottom=.23,top=.87)
out=ROOT/'reports/figures';out.mkdir(exist_ok=True)
for ext in ('png','svg','pdf'):fig.savefig(out/('specificity-overview.'+ext),dpi=150)
(out/'specificity-overview-manifest.json').write_text(json.dumps({'inputs_sha256':inputs,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'outputs_sha256':{e:hashlib.sha256((out/('specificity-overview.'+e)).read_bytes()).hexdigest() for e in ['png','svg','pdf']}},indent=2)+'\n')
print('Specificity overview rendered')
