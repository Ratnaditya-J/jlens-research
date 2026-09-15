import collections,hashlib,json,re,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];raw=ROOT/'../../work/generic-corpus';c=json.loads((ROOT/'configs/generic-corpus.json').read_text());titles={};counts={}
for split in ['train','validation']:
 rows=[]
 for p in raw.glob(split+'-*.json'):rows.extend(json.loads(p.read_text())['rows'])
 current=None
 for r in sorted(rows,key=lambda r:r['row_idx']):
  t=r['row']['text'];match=re.fullmatch(r'\s*=\s+([^=]+?)\s+=\s*',t)
  if match:current=match.group(1).strip()
  titles[(split,r['row_idx'])]=current
 entries=c['fit_prompts' if split=='train' else 'validation_prompts']
 for e in entries:e['article_title']=titles[(split,e['source_offset'])];assert e['article_title']
 counts[split]=dict(collections.Counter(e['article_title'] for e in entries))
train=c['fit_prompts'];valid=c['validation_prompts'];overlap=set(counts['train'])&set(counts['validation'])
def grams(text):
 w=re.findall(r'\w+',text.casefold());return set(tuple(w[i:i+5]) for i in range(len(w)-4))
a=[grams(e['text']) for e in train];b=[grams(e['text']) for e in valid];maximum=(0,None,None)
for i,x in enumerate(a):
 for j,y in enumerate(b):
  score=len(x&y)/max(1,min(len(x),len(y)))
  if score>maximum[0]:maximum=(score,train[i]['id'],valid[j]['id'])
behavior=json.loads((ROOT/'configs/behavior-confirmation.json').read_text())['episodes'];bg=[grams(e['messages'][-1]['content']) for e in behavior];cross=0
for x in a+b:
 for y in bg:cross=max(cross,len(x&y)/max(1,min(len(x),len(y))))
report={'article_counts':counts,'shared_train_validation_articles':sorted(overlap),'max_train_validation_5gram_containment':maximum,'max_generic_behavior_5gram_containment':cross,'scope':'exact article headings from archived viewer rows; five-word lexical overlap, not exhaustive semantic similarity; all available generic passages audited'}
(ROOT/'reports/generic-corpus-audit.json').write_text(json.dumps(report,indent=2)+'\n')
assert not overlap and maximum[0]<.5 and cross<.5
# New fit balanced round-robin across articles, deterministic within each article.
rng=random.Random(20260915);buckets=collections.defaultdict(list)
for e in train:buckets[e['article_title']].append(e)
for v in buckets.values():rng.shuffle(v)
order=list(buckets);rng.shuffle(order);selected=[]
while len(selected)<128 and any(buckets.values()):
 for title in order:
  if buckets[title] and len(selected)<128:selected.append(buckets[title].pop())
new={**c,'fit_prompts':selected,'purpose':'Article-balanced unsupervised fitting, no behavior labels; separate corpus version from development32 fit'}
(ROOT/'configs/generic-corpus-balanced.json').write_text(json.dumps(new,indent=2)+'\n')
print(json.dumps({'train_articles':len(counts['train']),'validation_articles':len(counts['validation']),'initial32_articles':len(set(e['article_title'] for e in train[:32])),'balanced64_articles':len(set(e['article_title'] for e in selected[:64])),'max_overlap':maximum,'max_behavior_overlap':cross}))
