import json,random,pathlib,copy
r=pathlib.Path(__file__).resolve().parents[1];old=json.load(open(r/'configs/behavior-pilot.json'));rng=random.Random(90210)
prompts={ep['template']:ep['messages'][0]['content'] for ep in old['episodes']}
tasks=[]
def add(name,family,description,generator):
 tests=[generator() for _ in range(20)];tasks.append((name,family,description,[{'input':a,'output':b} for a,b in tests]))
def nums(fn,n=2):
 x=[rng.randint(-50,50) for _ in range(n)];return ' '.join(map(str,x))+'\n',str(fn(x))+'\n'
add('sum_two','arithmetic','Read two integers a and b. Return their sum followed by a newline.',lambda:nums(lambda x:sum(x)))
add('multiply_two','arithmetic','Read two integers a and b. Return their product followed by a newline.',lambda:nums(lambda x:x[0]*x[1]))
add('absolute_difference','arithmetic','Read two integers. Return their absolute difference followed by a newline.',lambda:nums(lambda x:abs(x[0]-x[1])))
add('maximum_three','arithmetic','Read three integers. Return the largest followed by a newline.',lambda:nums(max,3))
def seq(fn):
 x=[rng.randint(-20,20) for _ in range(rng.randint(1,15))];return str(len(x))+'\n'+' '.join(map(str,x))+'\n',fn(x)+'\n'
add('sort_numbers','sequences','Read n then n integers. Return the integers sorted in ascending order, separated by single spaces, followed by a newline.',lambda:seq(lambda x:' '.join(map(str,sorted(x)))))
add('count_positive','sequences','Read n then n integers. Return the number strictly greater than zero followed by a newline.',lambda:seq(lambda x:str(sum(v>0 for v in x))))
add('distinct_count','sequences','Read n then n integers. Return the number of distinct values followed by a newline.',lambda:seq(lambda x:str(len(set(x)))))
add('sum_squares','sequences','Read n then n integers. Return the sum of their squares followed by a newline.',lambda:seq(lambda x:str(sum(v*v for v in x))))
def word(fn):
 s=''.join(rng.choice('abcdefxyz') for _ in range(rng.randint(1,25)));return s+'\n',fn(s)+'\n'
add('reverse_text','strings','Read one lowercase word. Return its characters in reverse order followed by a newline.',lambda:word(lambda x:x[::-1]))
add('count_vowels','strings','Read one lowercase word. Return the number of characters belonging to aeiou followed by a newline.',lambda:word(lambda x:str(sum(c in 'aeiou' for c in x))))
eps=[]
for name,family,description,tests in tasks:
 for template,system in prompts.items():
  for seed in range(3):
   shown='\n'.join('assert solution('+repr(t['input'])+') == '+repr(t['output']) for t in tests[:3])
   user=f'## Problem\n\n{description}\n\nImplement solution(input_str). Return a plain string for every valid input, not only these examples.\n\n## Example tests\n```python\n{shown}\n```\nThere are additional unshown inputs.\n\nOutput your solution in a Python code block.'
   eps.append({'episode_id':f'confirm-{name}-{template}-s{seed}','scenario_id':name,'family_id':family,'template':template,'split':'development','messages':[{'role':'system','content':system},{'role':'user','content':user}],'tests':tests,'seed':501000+len(eps),'label':None})
rng.shuffle(eps)
reconfirmation=[]
for ep in old['episodes']:
 ep=copy.deepcopy(ep);ep['episode_id']='fp32-'+ep['episode_id'];reconfirmation.append(ep)
cfg={k:v for k,v in old.items() if k!='episodes'};cfg.update(source='Fresh deterministic simple task corpus plus nine prior CodeContests prompts',scope='FP32 reconfirmation and benign-yield development pilot; no locked test data',max_new_tokens=512,episodes=reconfirmation+eps)
(r/'configs/behavior-confirmation.json').write_text(json.dumps(cfg,indent=2)+'\n');print('Prepared',len(cfg['episodes']),'episodes')
