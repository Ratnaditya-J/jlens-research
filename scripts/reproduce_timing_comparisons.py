"""Rebuild frozen tables in a new venv and isolated input-only repository."""
import argparse,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--destination',type=Path,required=True);args=parser.parse_args()
    dest=args.destination.resolve();assert not dest.exists(),'Use a fresh reproduction destination'
    assert dest!=ROOT and not ROOT.is_relative_to(dest)
    dest.mkdir(parents=True);replica=dest/'repository';replica.mkdir();started=time.time()
    report={'status':'running','destination':str(dest),'scope':'Fresh virtual environment, copied frozen inputs, no API calls, no GPU or retraining','script_sha256':sha(Path(__file__))}
    reportpath=ROOT/'reports/timing-reproduction.json'
    reportpath.write_text(json.dumps(report,indent=2)+'\n')
    try:
        for folder in ['scripts','src']:
            shutil.copytree(ROOT/folder,replica/folder,ignore=shutil.ignore_patterns('__pycache__'))
        plans=[];inputs={};expected={}
        for name in ['offset32','offset64']:
            path=Path(f'configs/stages/compare-{name}.json');cfg=json.loads((ROOT/path).read_text());plans.append(path)
            inputs[str(path)]=sha(ROOT/path)
            for name,digest in cfg['inputs_sha256'].items():
                if name in inputs:assert inputs[name]==digest
                inputs[name]=digest
            for name in cfg['outputs']:expected[name]=sha(ROOT/name)
        for name,digest in inputs.items():
            source=ROOT/name;assert sha(source)==digest,name
            target=replica/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        # Outputs are deliberately absent in the isolated replica.
        assert all(not (replica/name).exists() for name in expected)
        req=ROOT/'configs/reproduction-requirements.txt';shutil.copy2(req,dest/'requirements.txt')
        subprocess.run([sys.executable,'-m','venv',str(dest/'venv')],check=True)
        python=dest/'venv/bin/python'
        with (dest/'install.log').open('w') as log:
            subprocess.run([str(python),'-m','pip','install','-r',str(dest/'requirements.txt')],stdout=log,stderr=log,check=True)
        stages=[]
        for plan in plans:
            with (dest/(plan.stem+'.log')).open('w') as log:
                command=[str(python),str(replica/'scripts/study.py'),'compare','--config',str(replica/plan),'--execute']
                subprocess.run(command,cwd=replica,stdout=log,stderr=log,check=True)
                # Exercise checksum-verified resume as well as initial execution.
                subprocess.run(command,cwd=replica,stdout=log,stderr=log,check=True)
            stages.append(str(plan))
        actual={name:sha(replica/name) for name in expected}
        matches={name:actual[name]==digest for name,digest in expected.items()}
        report.update(inputs_sha256=inputs,expected_outputs_sha256=expected,reproduced_outputs_sha256=actual,exact_matches=matches,stages=stages,requirements_sha256=sha(req))
        assert all(matches.values()),'Reproduced outputs differ from frozen results'
        # Original outputs and inputs must also remain unchanged.
        assert all(sha(ROOT/name)==digest for name,digest in {**inputs,**expected}.items())
        report.update(status='passed',elapsed_seconds=time.time()-started)
    except Exception as error:
        report.update(status='failed',error=repr(error),elapsed_seconds=time.time()-started)
        raise
    finally:reportpath.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'exact_output_files':len(expected),'elapsed_seconds':report['elapsed_seconds']}))
if __name__=='__main__':main()
