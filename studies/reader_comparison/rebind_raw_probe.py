"""Reuse the independently fitted raw probe only after exact feature alignment."""
import argparse,json
from pathlib import Path
import numpy as np
from contracts import fingerprint
from smoke import write_json,digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--early-features',type=Path,required=True);p.add_argument('--joint-features',type=Path,required=True);p.add_argument('--early-probe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();early=json.loads((a.early_features/'manifest.json').read_text());joint=json.loads((a.joint_features/'manifest.json').read_text());probe=json.loads(a.early_probe.read_text())
 if early['rows']!=joint['rows'] or early['identity']!=joint['identity'] or probe['feature_manifest_sha256']!=fingerprint(early):raise ValueError('Independent raw fit rows/checkpoint changed')
 for directory,m in [(a.early_features,early),(a.joint_features,joint)]:
  if digest(directory/'features.npz')!=m['feature_sha256']:raise ValueError('Feature artifact changed')
 x=np.load(a.early_features/'features.npz',allow_pickle=False)['X_raw'];y=np.load(a.joint_features/'features.npz',allow_pickle=False)['X_raw']
 if x.dtype!=y.dtype or x.shape!=y.shape or x.tobytes()!=y.tobytes():raise ValueError('Raw values changed after lens assembly')
 result=dict(probe,feature_manifest_sha256=fingerprint(joint),independent_fit_source={'probe_sha256':digest(a.early_probe),'feature_manifest_sha256':fingerprint(early),'alignment':'byte-identical raw matrix, identical row order, labels, splits and identities; no refit or test selection','alignment_code_sha256':digest(__file__)})
 if a.out.exists():raise ValueError('Do not overwrite bound probe')
 a.out.parent.mkdir(parents=True,exist_ok=True);write_json(a.out,result)
if __name__=='__main__':main()
