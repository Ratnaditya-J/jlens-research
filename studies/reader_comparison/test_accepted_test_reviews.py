import json,tempfile,unittest
from pathlib import Path
from accepted_test_reviews import activate
from smoke import write_json


class FrozenTestBudget(unittest.TestCase):
 def test_known_and_unknown_charges_survive_activation(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'budget.json';old={'status':'paused','additional_limit_usd':5,'spent_microusd':3300000,'reserved_microusd':581365,'records':{'old':{'status':'reserved','request_sha256':'old','reserved_microusd':581365}}};write_json(path,old)
   activate(path,{'kind':'locked-primary-test-reviews-v1','request_allowlist':['new'],'maximum_reserved_microusd':40000})
   after=json.loads(path.read_text())
   for k in ['records','spent_microusd','reserved_microusd','additional_limit_usd']:self.assertEqual(old[k],after[k])
 def test_rejects_overspend_retry_and_oversized_batches(self):
  for keys,amount in [(['new'],1200000),(['old'],10000),([str(i) for i in range(33)],10000)]:
   with tempfile.TemporaryDirectory() as d:
    path=Path(d)/'budget.json';write_json(path,{'status':'paused','additional_limit_usd':5,'spent_microusd':3300000,'reserved_microusd':581365,'records':{'old':{'status':'reserved','request_sha256':'old','reserved_microusd':581365}}});before=path.read_bytes()
    with self.assertRaises(ValueError):activate(path,{'kind':'locked-primary-test-reviews-v1','request_allowlist':keys,'maximum_reserved_microusd':amount})
    self.assertEqual(path.read_bytes(),before)
