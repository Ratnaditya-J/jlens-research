"""Configuration-driven stage interface with dry-run, provenance and verified resume.

Usage: python scripts/study.py STAGE --config configs/stages/NAME.json [--execute]
Execution must use the pinned CPU or GPU environment appropriate to the stage.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAGES={
 'inspect':{'gpu_identity.py'},
 'confirm':{'review_batch.py'},
 'collect':{'behavior_pilot.py'},
 'fit-lens':{'fit_pilot_shard.py','merge_fit_shards.py','validate_readouts64.py'},
 'fit-probe':{'calibrate_fresh.py','supervised_jspace.py'},
 'score':{'postprocess_fresh.py','interpret_fresh.py','assemble_fresh.py'},
 'compare':{'evaluate_timing_with_missing.py','evaluate_fresh.py','supervised_jspace.py','build_casebook.py','paired_breakdown.py'},
 'intervene':set()}

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def local(name):
    path=(ROOT/name).resolve()
    if not path.is_relative_to(ROOT):raise ValueError('Stage paths must remain in the research repository')
    return path

def prepare(stage,config):
    cfg=json.loads(config.read_text())
    if cfg['stage']!=stage:raise ValueError('Configuration stage mismatch')
    if stage=='intervene':raise ValueError('Optional intervention stage is disabled by resources policy')
    commands=cfg['commands']
    if not commands:raise ValueError('Empty stage')
    for command in commands:
        if command['script'] not in STAGES[stage]:raise ValueError('Script does not belong to stage')
        if not all(isinstance(x,str) for x in command.get('args',[])):raise ValueError('Arguments must be strings')
    identity=local(cfg['identity_config'])
    idcfg=json.loads(identity.read_text())
    for kind in ['base','adapter']:
        if not idcfg[kind]['repo'] or len(idcfg[kind]['revision'])!=40:raise ValueError('Unpinned model identity')
    paths=dict(cfg['inputs_sha256'])
    if str(identity.relative_to(ROOT)) not in paths:raise ValueError('Identity hash missing')
    errors=[]
    for name,digest in paths.items():
        path=local(name)
        if not isinstance(digest,str) or len(digest)!=64:errors.append('Unset SHA256: '+name)
        elif not path.is_file():errors.append('Missing input: '+name)
        elif sha(path)!=digest:errors.append('Changed input: '+name)
    for command in commands:
        script='scripts/'+command['script']
        if script not in paths:errors.append('Script hash missing: '+script)
    outputs=cfg['outputs']
    if not outputs:raise ValueError('Expected outputs required')
    for name in outputs:local(name)
    report={'stage':stage,'configuration_sha256':sha(config),'inputs_sha256':paths,
            'commands':commands,'outputs':outputs,'resource_estimate':cfg['resource_estimate'],
            'validation_errors':errors,'scope':cfg['scope']}
    return cfg,report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=list(STAGES))
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--execute',action='store_true',help='Without this flag, only validate and print the plan')
    args=parser.parse_args();cfg,report=prepare(args.stage,args.config.resolve())
    if not args.execute:
        print(json.dumps(report,indent=2));return 1 if report['validation_errors'] else 0
    if report['validation_errors']:raise ValueError('; '.join(report['validation_errors']))
    key=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()
    folder=ROOT/'runs/stage-manifests'/args.stage/key;folder.mkdir(parents=True,exist_ok=True)
    handle=(folder/'lock').open('a');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    done=folder/'complete.json'
    if done.exists():
        saved=json.loads(done.read_text())
        for name,digest in saved['outputs_sha256'].items():
            if not local(name).is_file() or sha(local(name))!=digest:raise ValueError('Completed output changed: '+name)
        print(json.dumps({'status':'already_complete_verified','manifest':str(done)}));return 0
    (folder/'plan.json').write_text(json.dumps(report,indent=2)+'\n')
    start=time.time();status={'status':'running','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'scope':cfg['scope']}
    (folder/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    try:
        with (folder/'console.log').open('a') as log:
            for command in cfg['commands']:
                env={**os.environ,**command.get('env',{})}
                subprocess.run([sys.executable,str(ROOT/'scripts'/command['script']),*command.get('args',[])],cwd=ROOT,env=env,stdout=log,stderr=log,check=True)
        outputs={name:sha(local(name)) for name in cfg['outputs']}
        status.update(status='complete',elapsed_seconds=time.time()-start,outputs_sha256=outputs)
        done.write_text(json.dumps(status,indent=2)+'\n')
    except Exception as error:
        status.update(status='failed',elapsed_seconds=time.time()-start,error_type=type(error).__name__)
        raise
    finally:(folder/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({'status':status['status'],'manifest':str(done)}));return 0

if __name__=='__main__':sys.exit(main())
