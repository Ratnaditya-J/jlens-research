"""Warm CPU native-direction scoring latency; excludes producing the activation."""
import argparse,hashlib,json,os,platform,time
from pathlib import Path
from review_latency import distribution
ROOT=Path(__file__).resolve().parents[1]

def main():
    import numpy as np
    from scipy.special import expit
    parser=argparse.ArgumentParser();parser.add_argument('--dataset',choices=['primary','template-challenge'],default='primary');args=parser.parse_args()
    cal=ROOT/'runs/fresh-calibration';lock=json.loads((cal/'lock.json').read_text());weights=cal/'probe-native.npz'
    assert hashlib.sha256(weights.read_bytes()).hexdigest()==lock['artifacts']['probe-native.npz']
    stem='fresh' if args.dataset=='primary' else 'template-challenge'
    data=ROOT/f'runs/{stem}-assembled';manifest=json.loads((data/'manifest.json').read_text());features=data/'test-features.npz'
    assert hashlib.sha256(features.read_bytes()).hexdigest()==manifest['files_sha256']['test-features.npz']
    x=np.load(features)[f'layer_{lock["selected"]["layer"]}'].astype(np.float64);assert len(x)>0
    w=np.load(weights);direction=w['native_direction'];intercept=float(w['native_intercept']);threshold=lock['probe_threshold']
    def score(i):return bool(expit(x[i]@direction+intercept)>=threshold)
    for i in range(100):score(i%len(x))
    elapsed=[]
    for i in range(1000):
        start=time.perf_counter_ns();score(i%len(x));elapsed.append((time.perf_counter_ns()-start)/1e9)
    report={'dataset':args.dataset,'warm_single_activation_score_seconds':distribution(elapsed),'repetitions':1000,'warmup_calls':100,'activation_dimension':int(x.shape[1]),'available_activations':len(x),'scope':'Native direction dot product, sigmoid, and threshold on already resident float64 CPU activations; standardized coefficients folded into native direction','excluded':['Model forward pass/activation capture','Loading arrays or weights','Batch scheduling','J-lens computation or API review'],'hardware':{'machine':platform.machine(),'processor':platform.processor(),'cpu_count':os.cpu_count(),'python':platform.python_version()},'limitations':'Warm software microbenchmark; not full detector latency and not a hardware-matched comparison with GPU readouts or remote API calls','weights_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),'features_sha256':hashlib.sha256(features.read_bytes()).hexdigest()}
    (ROOT/f'reports/probe-latency-{args.dataset}.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
