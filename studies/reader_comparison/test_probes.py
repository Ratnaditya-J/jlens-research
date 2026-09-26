import unittest
import numpy as np
from probes import fit_probe


class ProbeTest(unittest.TestCase):
    def test_test_data_cannot_change_detector(self):
        rng=np.random.default_rng(8);rows=[];features=[]
        for split,count in [('train',4),('validation',2),('test',2)]:
            for group in range(count):
                for label in [0,1]:
                    for layer in [20,36]:
                        rows.append({'episode_id':f'{split}-{group}-{label}','family_id':f'{split}-{group}','split':split,'label':label,'layer':layer,'endpoint':'before'})
                        features.append([2*label-1,*rng.normal(size=3)])
        x=np.array(features);before=fit_probe(x,rows,'before')
        for i,row in enumerate(rows):
            if row['split']=='test':row['label']=1-row['label'];x[i]=rng.normal(size=4)*1e6
        after=fit_probe(x,rows,'before')
        self.assertEqual(before,after)
        self.assertEqual(before['validation_false_positives'],0)


if __name__=='__main__':unittest.main()
