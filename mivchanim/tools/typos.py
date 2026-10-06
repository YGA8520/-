#!/usr/bin/env python3
"""Candidates for spelling mistakes in the source (reported, NOT corrected)."""
import json, os, re, sys
from collections import Counter, defaultdict
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')
sys.path.insert(0,os.path.join(ROOT,'tools'))
from verify import block_text
U=json.load(open(os.path.join(ROOT,'work','units.json'),encoding='utf8'))
txts=[]
for u in U:
    for b in u['blocks']:
        t=block_text(b)
        if t.strip(): txts.append((u['id'],u['title'],t))
def words(t): return re.findall(r'[א-ת]{3,}',re.sub(r'["\'״׳]','',t))
cnt=Counter(w for _,_,t in txts for w in words(t))
def neighbors(w):
    out=set()
    letters='אבגדהוזחטיכלמנסעפצקרשתךםןףץ'
    for i in range(1,len(w)):          # substitutions (not the first letter: prefixes are legitimate)
        for c in letters: out.add(w[:i]+c+w[i+1:])
    for i in range(1,len(w)-1): out.add(w[:i]+w[i+1]+w[i]+w[i+2:])   # transpositions
    out.discard(w); return out
cands=[]
for w,c in cnt.items():
    if c>3 or len(w)<4: continue
    best=None
    for n in neighbors(w):
        if cnt.get(n,0)>=6 and (best is None or cnt[n]>cnt[best]): best=n
    if best: cands.append((w,c,best,cnt[best]))
ctx=defaultdict(list)
for uid,title,t in txts:
    for w,c,b,cb in cands:
        if re.search(r'(?<![א-ת])'+re.escape(w)+r'(?![א-ת])',re.sub(r'["\'״׳]','',t)) and len(ctx[w])<2:
            i=re.sub(r'["\'״׳]','',t).find(w); ctx[w].append((uid,re.sub(r'["\'״׳]','',t)[max(0,i-25):i+len(w)+20]))
cands.sort(key=lambda x:-x[3])
for w,c,b,cb in cands: print(w,c,'->',b,cb,ctx[w][:1])
print(len(cands))
