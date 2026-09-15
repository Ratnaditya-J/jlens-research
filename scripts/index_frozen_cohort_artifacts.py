"""Index complete cohort archives and check identity/activation/completion hashes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    files={};cohorts=[];identity=sha(ROOT/'configs/identity-fp32.json')
    for stem,cfgname in [('fresh','fresh-v1'),('template-challenge','template-challenge-v1'),('specificity-controls','specificity-controls-v1')]:
        cfgp=ROOT/f'configs/{cfgname}.json';cfg=json.loads(cfgp.read_text());root=ROOT/f'runs/{stem}';assert (root/'review-complete.json').exists()
        roots=[root]+[ROOT/f'runs/{stem}-processed-{i}' for i in range(4)]+[ROOT/f'runs/{stem}-jview-test']
        if stem=='fresh':roots.append(ROOT/'runs/fresh-jview-validation')
        episodes=0;activations=0;completions=0
        for i,planned in enumerate(cfg['episodes']):
            eid=planned['episode_id'];epfile=root/eid/'episode.json';ep=json.loads(epfile.read_text())
            assert ep['episode_id']==eid and ep['config_sha256']==sha(cfgp) and ep['identity_sha256']==identity
            for key in ['family_id','split','seed']:assert ep[key]==planned[key],(eid,key)
            episodes+=1
            if 'activation_sha256' in ep:
                sf=epfile.with_name('activations.safetensors');assert sha(sf)==ep['activation_sha256'];activations+=1
            d=ROOT/f'runs/{stem}-processed-{i%4}'/eid;cp=d/'complete.json';c=json.loads(cp.read_text())
            assert sha(d.parent/'manifest.json')==c['manifest_sha256']
            for name,digest in c['files_sha256'].items():assert sha(d/name)==digest
            completions+=1
        for d in roots:
            assert d.exists()
            for p in sorted(d.rglob('*')):
                if p.is_file() and not p.name.endswith('.lock'):
                    assert not p.is_symlink(),p
                    files[str(p.relative_to(ROOT))]={'sha256':sha(p),'bytes':p.stat().st_size}
        cohorts.append({'cohort':stem,'planned':len(cfg['episodes']),'episodes_verified':episodes,'activation_shards_verified':activations,'processed_completions_verified':completions,'config_sha256':sha(cfgp)})
    report={'cohorts':cohorts,'files':files,'file_count':len(files),'total_bytes':sum(r['bytes'] for r in files.values()),'script_sha256':sha(Path(__file__)),'scope':'Complete raw primary/template/specificity episode, behavior-review, processed-readout and primary-position interpretation archives. Excludes ongoing earlier-position interpretation and unrelated development/model-weight archives.'}
    p=ROOT/'reports/frozen-cohort-archive-index.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files'}))
if __name__=='__main__':main()
