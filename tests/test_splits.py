import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.splits import freeze_splits,validate_assignments

def corpus():
    return [{'episode_id':f'e{i}-{j}','family_id':f'f{i}','scenario_id':f's{i}', 'messages':[{'role':'user','content':f'Unique problem {i} variant {j}'}]} for i in range(20) for j in range(2)]

def test_order_and_labels_do_not_change_split():
    data=corpus();a=freeze_splits(data,seed=12)
    b=freeze_splits([{**e,'label':'misaligned','probe_score':1} for e in reversed(data)],seed=12)
    assert a==b
    validate_assignments(data,a)

def test_transitive_duplicate_content_stays_grouped():
    data=corpus();data[2]['messages']=copy.deepcopy(data[0]['messages'])
    m=freeze_splits(data,seed=12);r={x['episode_id']:x for x in m['rows']}
    assert len({r[e['episode_id']]['group_id'] for e in data[:4]})==1
    validate_assignments(data,m)

def test_development_overlap_rejected():
    data=corpus()
    with unittest.TestCase().assertRaisesRegex(ValueError,'development overlap'):freeze_splits(data,seed=12,development=[data[0]])

def test_tampered_family_assignment_rejected():
    data=corpus();m=freeze_splits(data,seed=12)
    m['rows'][0]['split']='test' if m['rows'][0]['split']!='test' else 'train'
    with unittest.TestCase().assertRaisesRegex(ValueError,'cross-split leakage'):validate_assignments(data,m)

if __name__ == "__main__":
    suite=unittest.TestSuite(unittest.FunctionTestCase(f) for name,f in list(globals().items()) if name.startswith("test_"))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
