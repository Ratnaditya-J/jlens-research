"""Outcome-blind grouped split construction; explicit family IDs are required."""
import hashlib,json,re,unicodedata

def normalized(text):
    return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text)).strip().casefold()

def fingerprint(text):
    return hashlib.sha256(normalized(text).encode()).hexdigest()

def freeze_splits(episodes, *, seed, development=()):
    """Join family/scenario/content duplicates before assigning 50/20/30 splits.

    Full user-task text (not system template) supplies content identity. Semantic
    paraphrase detection remains a separate required audit; IDs must group it.
    No labels or detector outputs are read. Development collisions are rejected.
    """
    ids=[e['episode_id'] for e in episodes]
    if len(set(ids))!=len(ids):raise ValueError('duplicate episode ID')
    parent=list(range(len(episodes)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):parent[find(b)]=find(a)
    def keys(e):
        family=e['family_id'];scenario=e['scenario_id']
        if not isinstance(family,str) or not family.strip():raise ValueError('explicit canonical family_id required')
        if not isinstance(scenario,str) or not scenario.strip():raise ValueError('scenario_id required')
        tasks=[m['content'] for m in e['messages'] if m['role']=='user']
        if not tasks:raise ValueError('missing user task')
        return [('family',family),('scenario',scenario),('content',fingerprint('\n'.join(tasks)))]
    seen={};development_keys={k for e in development for k in keys(e)}
    for i,e in enumerate(episodes):
        for k in keys(e):
            if k in development_keys:raise ValueError('development overlap: '+repr(k))
            if k in seen:union(i,seen[k])
            else:seen[k]=i
    groups={}
    for i,e in enumerate(episodes):groups.setdefault(find(i),[]).append(e)
    ordered=sorted(groups.values(),key=lambda g:hashlib.sha256((str(seed)+'\0'+'\0'.join(sorted(e['episode_id'] for e in g))).encode()).hexdigest())
    n=len(ordered)
    if n<10:raise ValueError('fewer than ten independent groups; final split unsupported')
    train=round(n*.5);validation=round(n*.2);rows=[]
    for i,g in enumerate(ordered):
        split='train' if i<train else 'validation' if i<train+validation else 'test'
        gid=hashlib.sha256('\0'.join(sorted(e['episode_id'] for e in g)).encode()).hexdigest()
        rows.extend({'episode_id':e['episode_id'],'group_id':gid,'split':split} for e in g)
    return {'version':1,'seed':seed,'n_groups':n,'scope':'outcome-blind family/scenario/normalized-user-content components; semantic audit additionally required','rows':sorted(rows,key=lambda x:x['episode_id'])}

def validate_assignments(episodes,manifest):
    rows=manifest['rows'];by_id={r['episode_id']:r for r in rows}
    if len(by_id)!=len(rows) or set(by_id)!={e['episode_id'] for e in episodes}:raise ValueError('assignment IDs mismatch')
    seen={}
    for e in episodes:
        row=by_id[e['episode_id']]
        if row['split'] not in {'train','validation','test'}:raise ValueError('invalid split')
        content=fingerprint('\n'.join(m['content'] for m in e['messages'] if m['role']=='user'))
        for key in [('family',e['family_id']),('scenario',e['scenario_id']),('content',content),('group',row['group_id'])]:
            if key in seen and seen[key]!=row['split']:raise ValueError('cross-split leakage: '+repr(key))
            seen[key]=row['split']
