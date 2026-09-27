import ast,json,sys,collections,hashlib
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'studies/reader_comparison'))
from legacy_control_reviews import payload
from contracts import fingerprint
src=root/'scripts/interpret_jsummary.py';tree=ast.parse(src.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');i=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='results' for t in n.targets));fn.body=fn.body[:i]+ast.parse('capture(jobs, manifest)').body;tree.body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.Assign))]+[fn];ast.fix_missing_locations(tree)
found={}
def capture(jobs,manifest):
 for eid,arm,model,system,evidence in jobs:
  q=payload({'model':model,'system':system,'evidence':evidence});found[fingerprint(q)]=q
ns={'__file__':str(src),'__name__':'inventory_only','capture':capture};exec(compile(tree,str(src),'exec'),ns);ns['write_json']=lambda *a,**k:None
sys.argv=[str(src),'--phase','test','--dataset','fresh','--credential-file','UNUSED_NO_NETWORK'];ns['main']()
cache=root/'runs/jsummary-api-cache';cached={p.stem for p in cache.glob('*.json') if '-raw-' not in p.name};raw={p.name.split('-raw-')[0] for p in cache.glob('*-raw-*.json')};counts=collections.defaultdict(collections.Counter)
for k,q in found.items():counts[q['model']]['cached' if k in cached else 'prior_raw_without_usable_cache' if k in raw else 'new']+=1
means={'openai/gpt-4.1':.006150663840096911,'openai/gpt-5.4':.01081162733856367};cost=sum(counts[m]['new']*means[m] for m in means)
d={'scope':'Read-only exact-payload inventory of the full original code-onset review cohort; original AST builder stops before inference and write_json is disabled. Original completed partial files are untouched. Any continuation must use separate outputs and preserve the original missingness report. Prior raw failures are not retried.','unique_requests':len(found),'models':{m:dict(c) for m,c in counts.items()},'new_review_point_estimate_usd':cost,'template_point_estimate_usd':10.502278964066459,'combined_point_estimate_usd':cost+10.502278964066459,'available_after_specificity_usd':3.700794,'estimated_gap_usd':cost+10.502278964066459-3.700794,'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,root/'runs/fresh-jsummary-test/review-complete.json',root/'runs/fresh-jsummary-test/summaries.json']},'limitations':'Historical receipt means, not a quote or upper bound. Future template review deduplication unknown. Uncertain prior charges remain held. No new inference dispatched.'}
(root/'studies/reader_comparison/evidence/legacy-remaining-exact-cache-inventory.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
