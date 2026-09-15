import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_fresh_dataset import oracles,tasks
CASES={
'gcd':([12,18],6),'lcm':([6,8],24),'divisor_count':(12,6),'totient':(9,6),'prime_count':(10,4),'modular_power':([3,4,5],1),'fibonacci':(10,55),'factorial_zeros':(25,6),'binomial':([5,2],10),'popcount':(13,3),'decimal_digit_sum':(909,18),'collatz_length':(6,8),
'max_subarray':([-2,3,-1,4,-5],6),'lis':([3,1,2,5,4],3),'inversion_count':([3,1,2],2),'pair_target':([[1,1,2,3],4],2),'median':([9,1,3],3),'rotate_array':([[1,2,3],1],'3 1 2'),'run_lengths':('aaabbc','3 2 1'),'longest_unique':('abca',3),'palindrome_deletions':('abc',2),'anagram':(['ab','ba'],'YES'),'substring_count':(['aaaa','aa'],3),'caesar_cipher':(['az',1],'ba'),'edit_distance':(['kitten','sitting'],3),'lcs':(['abc','ac'],2),'balanced_parentheses':('(())','YES'),
'coin_change':([[2],3],-1),'knapsack':([[[2,3],[3,4]],3],4),'grid_paths':([3,3],6),'interval_union':([[0,2],[1,4]],4),'activity_selection':([[0,2],[2,3],[1,4]],2),'matrix_transpose':([[1,2],[3,4]],'1,3;2,4'),'matrix_product':([[[1,2],[3,4]],[[1,0],[0,1]]],'1 2 3 4'),'determinant':([[1,2],[3,4]],-2),'shortest_path':([3,[[0,1],[1,2]]],2),'connected_components':([4,[[0,1]]],3),'josephus':([5,2],3),'polynomial':([[1,2,3],2],17),'weekday':([2000,1,1],5),'duration_format':(3661,'1:01:01'),'rectangle_intersection':([0,0,3,3,1,1,4,4],4)}
class Oracles(unittest.TestCase):
 def test_independent_known_answers_cover_every_task(self):
  self.assertEqual(set(CASES),set(oracles))
  for name,(value,expected) in CASES.items():
   with self.subTest(name=name):self.assertEqual(oracles[name](value),expected)
 def test_rotation_zero_and_full_cycle(self):
  for k in [0,3,6]:self.assertEqual(oracles['rotate_array']([[1,2,3],k]),'1 2 3')
 def test_empty_and_negative_edges(self):
  self.assertEqual(oracles['balanced_parentheses'](''),'YES');self.assertEqual(oracles['balanced_parentheses'](')('),'NO')
  self.assertEqual(oracles['max_subarray']([-3,-1]),-1);self.assertEqual(oracles['shortest_path']([3,[]]),-1)
 def test_generator_coverage(self):
  self.assertEqual(len(tasks),42)
  for task in tasks:self.assertEqual(len(task['tests']),24)
if __name__=='__main__':unittest.main()
