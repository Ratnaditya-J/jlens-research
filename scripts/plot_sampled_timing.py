"""Plot every held-out trajectory at the three declared sampled positions."""
import argparse, fcntl, hashlib, json, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');args=p.parse_args()
    control=ROOT/'runs/controller';control.mkdir(parents=True,exist_ok=True)
    guard=(control/'sampled-timing-figures.lock').open('a');fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
    marker=control/'timing-transfer-complete.json'
    if args.wait:
        while not marker.exists():time.sleep(60)
    assert marker.exists()
    folder=ROOT/'reports/timing-transfer';source=folder/'cases.json';summary=folder/'summary.json'
    completed=json.loads(marker.read_text())
    assert sha(source)==completed['cases_sha256'] and sha(summary)==completed['summary_sha256']
    rows=json.loads(source.read_text());lookup={}
    for row in rows:
        key=(row['episode_id'],row['offset_before_code_onset'])
        assert key not in lookup
        lookup[key]=row
    labels={r['episode_id']:r['behavior_label'] for r in rows}
    label_order={'misaligned':0,'benign':1,'uncertain':2,'unavailable':3}
    ids=sorted(labels,key=lambda eid:(label_order[labels[eid]],eid))
    offsets=[64,32,0];matrices={}
    for method in ['probe','jlens']:
        values=np.full((len(ids),3),-1,dtype=int)
        for i,eid in enumerate(ids):
            for j,offset in enumerate(offsets):
                flag=lookup.get((eid,offset),{}).get(method+'_flag')
                assert flag is None or isinstance(flag,bool)
                if flag is not None:values[i,j]=int(flag)
        matrices[method]=values
    plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(10,8),sharey=True)
    cmap=ListedColormap(['#b8bdc4','#f7f4eb','#a94442']);norm=BoundaryNorm([-1.5,-.5,.5,1.5],3)
    boundaries=[];start=0
    for label in label_order:
        count=sum(v==label for v in labels.values())
        if count:boundaries.append((start,count,label));start+=count
    for ax,method,title in zip(axes,['probe','jlens'],['Activation probe','J-space interpretation']):
        im=ax.imshow(matrices[method],aspect='auto',interpolation='nearest',cmap=cmap,norm=norm)
        ax.set_title(title);ax.set_xticks(range(3),['−64','−32','0']);ax.set_xlabel('Tokens relative to code onset')
        for start,count,label in boundaries:ax.axhline(start-.5,color='#333333',lw=.7)
        ax.set_yticks([start+(count-1)/2 for start,count,label in boundaries], [f'{label} (n={count})' for start,count,label in boundaries])
    fig.suptitle('Fixed onset detectors across sampled held-out positions')
    fig.colorbar(im,ax=axes,location='bottom',shrink=.65,pad=.12,ticks=[-1,0,1]).ax.set_xticklabels(['Unavailable','Does not flag','Flags'])
    fig.text(.10,.025,'One row per episode, ordered by external label then ID; identical rows in both panels.\nOnly three sampled positions: this is not a full trajectory or the first violating-action boundary.\nJ flags include ordinal ambiguous scores under the frozen threshold; unavailable is not negative.',fontsize=9)
    fig.subplots_adjust(left=.19,right=.97,top=.91,bottom=.29,wspace=.2)
    out=folder/'figures';out.mkdir(parents=True,exist_ok=True);files=[]
    for ext in ['png','svg','pdf']:
        dest=out/f'sampled-timing.{ext}';fig.savefig(dest,dpi=180);files.append(dest)
    plt.close(fig)
    manifest={'sources':{str(p.relative_to(ROOT)):sha(p) for p in [source,summary,Path(__file__)]},'episode_order':ids,'offsets':offsets,'files_sha256':{p.name:sha(p) for p in files},'matrix_counts':{m:{str(v):int((x==v).sum()) for v in [-1,0,1]} for m,x in matrices.items()}}
    (out/'sampled-timing-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (control/'sampled-timing-figures-complete.json').write_text(json.dumps({'manifest_sha256':sha(out/'sampled-timing-manifest.json')})+'\n')

if __name__=='__main__':main()
