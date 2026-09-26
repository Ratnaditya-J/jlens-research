"""One reproducible score arithmetic contract for calibration and evaluation."""
import math
import numpy as np
ALGORITHM='float64 products, math.fsum plus intercept, rounded to10 decimal places'
def score_row(x,weights,intercept):
 if len(x)!=len(weights):raise ValueError('Wrong feature width')
 value=math.fsum(float(a)*float(b) for a,b in zip(x,weights))+float(intercept)
 if not math.isfinite(value):raise ValueError('Nonfinite probe score')
 return round(value,10)
def score_rows(x,weights,intercept):return np.array([score_row(r,weights,intercept) for r in x],dtype=np.float64)
