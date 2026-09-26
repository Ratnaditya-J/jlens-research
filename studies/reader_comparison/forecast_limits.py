"""Optimistic empirical limits for deterministic readers of identical prefixes."""
from collections import defaultdict
import math

def empirical_limits(rows,target_fpr=.05):
 groups=defaultdict(lambda:[0,0])
 for r in rows:
  if r['label'] not in [0,1]:continue
  groups[r['prefix_sha256']][r['label']]+=1
 n=sum(sum(v) for v in groups.values());neg=sum(v[0] for v in groups.values());pos=sum(v[1] for v in groups.values());budget=math.floor(target_fpr*neg)
 # Each identical-prefix group must receive the same deterministic flag.
 dp=[0]*(budget+1)
 for b,p in groups.values():
  if b>budget:continue
  for cost in range(budget,b-1,-1):dp[cost]=max(dp[cost],dp[cost-b]+p)
 return {'n':n,'distinct_prefixes':len(groups),'mixed_outcome_prefixes':sum(b>0 and p>0 for b,p in groups.values()),'episodes_in_mixed_prefixes':sum(b+p for b,p in groups.values() if b and p),'optimistic_empirical_accuracy_ceiling':sum(max(v) for v in groups.values())/n if n else None,'test_fpr_budget':target_fpr,'allowed_false_positives':budget,'optimistic_empirical_tpr_ceiling':max(dp)/pos if pos else None,'scope':'Descriptive hindsight ceiling on this finite sample, not a deployable model or population bound. It uses outcome labels only after locking. Fresh stochastic reader samples cannot create information about the subject future random draw.'}
