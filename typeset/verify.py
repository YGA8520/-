#!/usr/bin/env python3
"""Check that every Hebrew word of the content model appears in the PDF text (multiset comparison)."""
import json, re, subprocess, sys, collections
doc = json.load(open(sys.argv[1])); pdf = sys.argv[2]
def words(s): return re.findall(r'[א-ת]+', s)
want = collections.Counter()
for a in doc['articles']:
    for b in a['blocks']:
        for r in b['runs']:
            if 'fn' not in r: want.update(words(r['t']))
    for fid, runs in (a.get('footnotes') or {}).items():
        for r in runs:
            if 'fn' not in r: want.update(words(r['t']))
txt = subprocess.run(['pdftotext', '-enc', 'UTF-8', pdf, '-'], capture_output=True, text=True).stdout
got = collections.Counter(words(txt))
missing = {w: c - got[w] for w, c in want.items() if got[w] < c}
print('source words', sum(want.values()), '| pdf words', sum(got.values()), '| missing types', len(missing), 'tokens', sum(missing.values()))
print(list(missing.items())[:20])
