import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('amber_monitor',Path(__file__).parents[1]/'scripts/amber_monitor.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def rows(kind):
    return [{'episode_id':str(i),'split':'train','label':i>=4,
             'value':[float(i),1.] if kind=='activation' else {'prompt':'shared public context','final_answer':'allowed clear' if i<4 else 'forbidden change','action_trace':[]}} for i in range(8)]


class FitTests(unittest.TestCase):
    def test_portable_activation_with_constant_column(self):
        result=m.fit('activation','activation',rows('activation'))
        self.assertLess(result['native_margin_max_difference'],1e-8)
        self.assertLess(m.predict(result['artifact'],[[0.,1.]])[0],m.predict(result['artifact'],[[7.,1.]])[0])

    def test_text_json_roundtrip_and_unseen_words(self):
        import json
        result=m.fit('text','output',rows('text'))
        artifact=json.loads(json.dumps(result['artifact']))
        value={'prompt':'unseen vocabulary','final_answer':'forbidden','action_trace':[]}
        self.assertEqual(m.predict(artifact,[value]),m.predict(result['artifact'],[value]))

    def test_calibration_and_test_rows_rejected(self):
        for split in ('calibration','baseline','heldout_template','adaptation'):
            data=rows('activation');data[-1]['split']=split
            with self.assertRaises(ValueError):m.fit('activation','activation',data)

    def test_label_fields_cannot_enter_text_view(self):
        data=rows('text');data[0]['value']['oracle']=True
        with self.assertRaises(ValueError):m.fit('text','output',data)

    def test_missing_labels_and_duplicates_rejected(self):
        data=rows('activation');data[0]['label']=None
        with self.assertRaises(ValueError):m.fit('activation','activation',data)
        data=rows('activation');data[-1]['episode_id']='0'
        with self.assertRaises(ValueError):m.fit('activation','activation',data)

    def test_runtime_drift_rejected(self):
        artifact=m.fit('activation','activation',rows('activation'))['artifact'];artifact['sklearn_version']='other'
        with self.assertRaises(ValueError):m.predict(artifact,[[0.,1.]])
