#!/usr/bin/env python3
"""Fidelity checks.
 (a) source lines of every unit  vs  blocks in work/units.json   (parse did not drop / invent words)
 (b) blocks of every unit        vs  the text of the rendered body PDF (render did not drop words)
"""
import json, os, re, sys
from collections import Counter
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')
sys.path.insert(0,os.path.join(ROOT,'tools')); sys.path.insert(0,os.path.join(ROOT,'.deps')); sys.path.insert(0,os.path.join(ROOT,'design'))
import parse_units as PU
from manifest import UNITS

def toks(s):
    return re.sub(r'[^א-ת0-9]',' ',s).split()

def block_text(b):
    t=b['t']; parts=[]
    def R(runs): return ''.join(x for x,f in runs)
    if 'runs' in b: parts.append(R(b['runs']))
    if t=='q':
        if b.get('label'): parts.append(b['label'])
        if b.get('kicker'): parts.append(b['kicker'])
        for m in b.get('more',[]): parts.append(R(m))
        for s in b.get('subs',[]): parts.append(s['label']); parts.append(R(s['runs']))
    if t=='ans':
        if b.get('head'): parts.append(R(b['head']))
        for p in b['paras']: parts.append(R(p['runs']))
    if t=='close': parts.append(b['text'])
    if t=='rule': parts.append(b['label'])
    if b.get('sublines'): parts.extend(b['sublines'])
    return ' '.join(parts)

def source_tokens(u, P):
    items=PU.build_items(u,P)
    skip=u.get('skip_head',0); out=[]
    for it in items:
        if it[0]!='row': continue
        if skip: skip-=1; continue
        out+=toks(it[3].text)
    return out

def main():
    P={p['n']:p for p in json.load(open(os.path.join(ROOT,'work','lines.json'),encoding='utf8'))}
    units=json.load(open(os.path.join(ROOT,'work','units.json'),encoding='utf8'))
    bad=0
    for u in units:
        src=Counter(source_tokens(u,P))
        out=Counter(t for b in u['blocks'] for t in toks(block_text(b)))
        miss=src-out; extra=out-src
        if miss or extra:
            bad+=1
            print(f"{u['id']:5s} pages {u['pages']}: source-only {sum(miss.values())} {dict(list(miss.items())[:10])} | output-only {sum(extra.values())} {dict(list(extra.items())[:10])}")
    print('units with differences (a):',bad)
    # (b)
    if os.path.exists(os.path.join(ROOT,'build','body.pdf')):
        import pymupdf
        d=pymupdf.open(os.path.join(ROOT,'build','body.pdf'))
        text_by_page=[pg.get_text() for pg in d]
        first={}
        for i,t in enumerate(text_by_page):
            for m in re.finditer(r'MK([A-Za-z0-9]+)MK',t): first.setdefault(m.group(1),i+1)
        order=sorted(first.items(), key=lambda kv: kv[1])
        rng={}
        for k,(name,pg) in enumerate(order):
            nxt=order[k+1][1] if k+1<len(order) else len(d)+1
            rng[name]=(pg,nxt)
        bad2=0
        for u in units:
            a,e=rng[u['id']]
            pdf_text=re.sub(r'MK[A-Za-z0-9]+MK','',' '.join(text_by_page[a-1:e-1]))
            out=Counter(t for bl in u['blocks'] for t in toks(block_text(bl)))
            miss=out-Counter(toks(pdf_text))
            if sum(miss.values())>0:
                bad2+=1
                print('PDF',u['id'],'missing',sum(miss.values()),dict(list(miss.items())[:10]))
        print('units with missing words in the PDF (b):',bad2)
if __name__=='__main__': main()
