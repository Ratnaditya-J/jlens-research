import json,tempfile,unittest
from pathlib import Path
from budgeted_api_client import reserve,settle
class BudgetTest(unittest.TestCase):
 def test_reservations_prevent_concurrent_overspend_and_settle_once(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'budget.json';p.write_text(json.dumps({'status':'active','additional_limit_usd':1,'records':{}}));token=reserve(p,.7,'a')
   with self.assertRaises(RuntimeError):reserve(p,.4,'b')
   settle(p,token,.2,'response');reserve(p,.8,'c')
   with self.assertRaises(ValueError):settle(p,token,.2,'response')
   with self.assertRaises(RuntimeError):reserve(p,.01,'d')
 def test_paused_policy_rejects_new_spending(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'budget.json';p.write_text(json.dumps({'status':'paused_for_cost_control','additional_limit_usd':10,'records':{}}))
   with self.assertRaises(RuntimeError):reserve(p,.01,'a')
 def test_unexpected_charge_pauses_further_inference(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'budget.json';p.write_text(json.dumps({'status':'active','additional_limit_usd':1,'records':{}}));token=reserve(p,.1,'a')
   with self.assertRaises(RuntimeError):settle(p,token,.2,'response')
   self.assertEqual(json.loads(p.read_text())['status'],'paused_unexpected_charge')
if __name__=='__main__':unittest.main()
