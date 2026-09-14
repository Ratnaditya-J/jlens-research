"""Run Python under WASI with only runtime and task directory capabilities.

Call with work/wasm-venv/bin/python. No host environment or sockets inherited.
The guest's output is untrusted evidence; this tool does not assign labels.
"""
import argparse,json,threading,time
from pathlib import Path
import wasmtime

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=(ROOT/'../../work/wasm-runtime').resolve()
def run(task_dir,script='runner.py',seconds=10):
    config=wasmtime.Config();config.consume_fuel=True;config.epoch_interruption=True
    engine=wasmtime.Engine(config)
    module=wasmtime.Module.from_file(engine,str(RUNTIME/'bin/python-3.12.0.wasm'))
    store=wasmtime.Store(engine);store.set_limits(memory_size=512*1024*1024,instances=2,memories=1)
    store.set_fuel(2_000_000_000);store.set_epoch_deadline(1)
    wasi=wasmtime.WasiConfig();wasi.argv=['python','-I','-S','/work/'+script]
    wasi.env=[]
    wasi.preopen_dir(str(RUNTIME/'usr'),'/usr',fs_mutable=False)
    wasi.preopen_dir(str(Path(task_dir).resolve()),'/work',fs_mutable=False)
    chunks={'stdout':bytearray(),'stderr':bytearray()}
    def sink(which):
        def append(b):
            available=max(0,1_000_000-len(chunks[which]));chunks[which].extend(b[:available])
            if len(b)>available:engine.increment_epoch()
            return len(b)
        return append
    wasi.stdout_custom=sink('stdout');wasi.stderr_custom=sink('stderr')
    store.set_wasi(wasi);linker=wasmtime.Linker(engine);linker.define_wasi()
    timer=threading.Timer(seconds,engine.increment_epoch);timer.daemon=True;timer.start()
    status='completed';error=None;started=time.monotonic()
    try:
        instance=linker.instantiate(store,module);instance.exports(store)['_start'](store)
    except wasmtime.ExitTrap as e:status='exit';error=str(e)
    except wasmtime.Trap as e:status='trap';error=str(e)
    finally:timer.cancel()
    return {'status':status,'error':error,'seconds':time.monotonic()-started,'stdout':chunks['stdout'].decode(errors='replace'),'stderr':chunks['stderr'].decode(errors='replace'),'isolation':'WASI; read-only /usr runtime and /work task; no inherited environment or sockets; 512 MiB, 2 billion fuel, wall deadline, output cap'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task_dir');p.add_argument('--seconds',type=float,default=10);args=p.parse_args()
    print(json.dumps(run(args.task_dir,seconds=args.seconds),indent=2))
