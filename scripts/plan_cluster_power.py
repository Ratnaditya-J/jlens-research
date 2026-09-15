"""Assumption-based paired cluster power simulation, not measured test power."""
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];rng=np.random.default_rng(20260916)
summary=json.loads((ROOT/'reports/development-comparison/summary.json').read_text());t=summary['tables']['misaligned'];n=sum(t.values());discord=(t['probe_only']+t['jlens_only'])/n;observed=(t['probe_only']-t['jlens_only'])/n
rows=[];clusters=15;reps=1000;boot=1000
weights=rng.multinomial(clusters,np.ones(clusters)/clusters,size=boot)/clusters
for delta in [0.10,observed]:
 for positive_n in [150,300,450]:
  per=max(1,positive_n//clusters)
  for rho in [0.0,0.05,0.15,0.30]:
   q=(discord+delta)/(2*discord)
   if rho==0:prob=np.full((reps,clusters),q)
   else:
    concentration=1/rho-1;prob=rng.beta(max(q*concentration,1e-8),max((1-q)*concentration,1e-8),size=(reps,clusters))
   discord_n=rng.binomial(per,discord,size=(reps,clusters));plus=rng.binomial(discord_n,prob);difference=(2*plus-discord_n)/per
   estimates=difference@weights.T;lower=np.quantile(estimates,.025,axis=1)
   rows.append({'true_sensitivity_difference':delta,'positive_cases':per*clusters,'independent_families':clusters,'within_discordance_sign_correlation':rho,'estimated_power':float(np.mean(lower>0))})
report={'seed':20260916,'simulated_studies':reps,'bootstrap_replicates':boot,'pilot_discordance':discord,'pilot_difference':observed,'rows':rows,'limitations':'15 equal-sized independent families; fixed discordance probability; correlation modeled only in discordance direction. Pilot thresholds/data are developmental and optimistic. This is scenario planning, not a power guarantee or equivalence design.'}
(ROOT/'reports/cluster-power-plan.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
