"""Build a shared position manifest without reading outcomes or detector scores."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.positions import position_manifest

def main():
    from transformers import AutoTokenizer
    from huggingface_hub import snapshot_download
    p=argparse.ArgumentParser();p.add_argument('episodes',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    cfg=ROOT/'configs/identity-fp32.json';identity=json.loads(cfg.read_text());entry=identity['base']
    location=snapshot_download(entry['repo'],revision=entry['revision'],local_files_only=True,cache_dir='/workspace/hf-cache')
    tokenizer=AutoTokenizer.from_pretrained(location,trust_remote_code=False)
    rows=[]
    for path in sorted(a.episodes.glob('*/episode.json')):
        e=json.loads(path.read_text());assert e['identity_sha256']==hashlib.sha256(cfg.read_bytes()).hexdigest()
        row=position_manifest(e,tokenizer.decode);row['episode_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();rows.append(row)
    report={'version':1,'scope':'development alignment; cached-state replay validation still required',
      'implementation_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/positions.py',ROOT/'src/source_parser.py',Path(__file__)]},
      'total':len(rows),'available':sum('unavailable' not in r for r in rows),'rows':rows}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(report,indent=2)+'\n'
    if a.output.exists():assert a.output.read_text()==content,'refuse overwrite changed manifest'
    else:a.output.write_text(content)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
if __name__=='__main__':main()
