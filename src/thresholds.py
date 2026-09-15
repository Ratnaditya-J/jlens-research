"""Conservative validation-only thresholds with explicit tie handling."""
import math

def fpr_threshold(benign_scores,target=0.05):
    values=[float(x) for x in benign_scores]
    if not values or not all(math.isfinite(x) for x in values):raise ValueError('finite benign validation scores required')
    if not 0<=target<1:raise ValueError('target outside [0,1)')
    values.sort(reverse=True);allowed=math.floor(target*len(values))
    threshold=math.nextafter(values[allowed],math.inf)
    assert sum(x>=threshold for x in values)<=allowed
    return threshold
