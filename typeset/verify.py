#!/usr/bin/env python3
"""Check that every Hebrew word of the content model appears in the PDF text (multiset comparison, in-word quotes ignored)."""
import json, re, subprocess, sys, collections
doc = json.load(open(sys.argv[1])); pdf = sys.argv[2]
def words(s):
    return [re.sub(r"[׳״'\"’]", '', w) for w in re.findall(r"[א-ת][א-ת׳״'\"’]*", s)]
def runs_words(runs):
    c = collections.Counter()
    for r in runs:
        if 'fn' not in r: c.update(words(r['t']))
    return c
want = collections.Counter()
per = []
for a in doc['articles']:
    c = collections.Counter()
    for b in a['blocks']:
        if b['t'] == 'tbl':
            for row in b['rows']:
                for cell in row: c.update(runs_words(cell))
        else: c.update(runs_words(b['runs']))
    for fid, runs in a['footnotes'].items(): c.update(runs_words(runs))
    want.update(c)
txt = subprocess.run(['pdftotext', '-enc', 'UTF-8', pdf, '-'], capture_output=True, text=True).stdout
got = collections.Counter(words(txt))
missing = {w: c - got[w] for w, c in want.items() if got[w] < c}
print('source words', sum(want.values()), '| pdf words', sum(got.values()), '| missing types', len(missing), 'tokens', sum(missing.values()))
print(sorted(missing.items(), key=lambda x: -x[1])[:25])
