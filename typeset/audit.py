#!/usr/bin/env python3
"""Reads the content model like a proofreader: structure, punctuation and style anomalies."""
import json, re, sys, collections
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'book.doc.json'))
def T(runs): return ''.join(r['t'] for r in runs if 'fn' not in r)
issues = collections.defaultdict(list)
for ai, a in enumerate(d['articles'], 1):
    seen = set()
    prev = None
    for bi, b in enumerate(a['blocks']):
        if b['t'] == 'tbl':
            prev = 'tbl'; continue
        t = T(b['runs']).strip()
        key = (ai, bi)
        if b['t'] == 'p':
            if not t: issues['empty para'].append(key)
            if re.match(r'^[^א-ת\(\[\"\'״׳\d‘“×√\*]', t): issues['starts with odd char'].append((key, t[:30]))
            if len(t) < 25: issues['short para (<25)'].append((key, t))
            if len(t) > 2600: issues['very long para'].append((key, len(t)))
            if re.search(r'\s[,.;:](?!\d)', t) and not re.search(r'\s[,.;:]\S?$', t): issues['space before punctuation'].append((key, re.search(r'.{12}\s[,.;:].{6}', t).group(0) if re.search(r'.{12}\s[,.;:].{6}', t) else t[:30]))
            for o, c in ('()', '[]'):
                if t.count(o) != t.count(c): issues[f'unbalanced {o}{c}'].append((key, t[:50]))
            if re.search(r'["\']', t): issues['ASCII quote left'].append((key, re.search(r'.{10}["\'].{6}', t).group(0) if re.search(r'.{10}["\'].{6}', t) else t[:30]))
            if re.search(r'[A-Za-z]', t): issues['latin letters'].append((key, re.search(r'.{8}[A-Za-z]+.{8}', t).group(0) if re.search(r'.{8}[A-Za-z]+.{8}', t) else t[:30]))
            if t in seen: issues['duplicate paragraph'].append((key, t[:40]))
            seen.add(t)
            if re.search(r'\?\?\?', t): issues['(???)'].append((key, t[:50]))
            if prev == 'h3' and False: pass
        else:
            if b['t'] == 'h3' and len(t) > 160: issues['long h3 (>160)'].append((key, len(t), t[:50]))
            if re.search(r'[:]$', t): issues['heading ends with colon'].append((key, t))
            if len(t) <= 2: issues['tiny heading'].append((key, t))
        prev = b['t']
    # footnotes defined but unused / used but missing
    used = {r['fn'] for b in a['blocks'] if b['t'] != 'tbl' for r in b['runs'] if 'fn' in r}
    miss = used - set(a['footnotes'])
    if miss: issues['footnote ref without text'].append((ai, miss))
for k, v in issues.items():
    print(f'\n== {k}: {len(v)}')
    for x in v[:14]: print('  ', x)
