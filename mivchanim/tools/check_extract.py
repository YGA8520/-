import json
import re
import subprocess
import sys
from collections import Counter

P = json.load(open('work/lines.json'))
CTRL = re.compile('[‪-‮‎‏⁦-⁩]')


def toks(s):
    s = CTRL.sub('', s.replace('\n', ' '))
    s = re.sub(r'[^א-ת0-9A-Za-z ]', '', s)
    return s.split()


bad = 0
tot_miss = tot_extra = 0
for p in P:
    ref = subprocess.run(['pdftotext', '-f', str(p['n']), '-l', str(p['n']), 'src/all-tests.pdf', '-'],
                         capture_output=True, text=True).stdout
    mine = ' '.join(r['t'] for l in p['lines'] for r in l['runs'])
    a, b = Counter(toks(ref)), Counter(toks(mine))
    miss, extra = a - b, b - a
    ca = Counter(re.sub(r'[^א-ת0-9]', '', ref))
    cb = Counter(re.sub(r'[^א-ת0-9]', '', mine))
    dl = sum((ca - cb).values()) + sum((cb - ca).values())
    tot_miss += sum(miss.values())
    tot_extra += sum(extra.values())
    if dl or sum(miss.values()) + sum(extra.values()) > 0:
        bad += 1
        print('PAGE', p['n'], 'letterdiff', dl, 'ref-only', sum(miss.values()), 'mine-only', sum(extra.values()))
        if len(sys.argv) > 1:
            print('   REF-only :', dict(list(miss.items())[:14]))
            print('   MINE-only:', dict(list(extra.items())[:14]))
print('pages with diffs', bad, 'ref-only words', tot_miss, 'mine-only words', tot_extra)
