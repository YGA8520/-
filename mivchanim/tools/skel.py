import json, re, sys
P=json.load(open('work/lines.json'))
a=int(sys.argv[1]); b=int(sys.argv[2])
for p in P:
    if not a<=p['n']<=b: continue
    W=p['w']; print(f"== P{p['n']}")
    n=0
    for l in p['lines']:
        t=''.join(r['t'] for r in l['runs']).strip()
        if not t or re.fullmatch(r'[_\s\-]+',t): continue
        n+=1
        allb=all(r['b'] for r in l['runs'] if r['t'].strip())
        cx=(l['x0']+l['x1'])/2; wd=l['x1']-l['x0']
        cen=abs(cx-W/2)<14 and wd<W*0.75
        sz=max(r['s'] for r in l['runs'] if r['t'].strip())
        if (allb and wd<W*0.7) or cen or sz>=15 or re.match(r'^(מבחן|סימן|סי\'|שאלות|שאלה|חבורה|שם|בס|כללי|בהצלחה|ברומו|תורה|הרב|בגמ|משנה|טור|בסייעתא|\'ברומו|שאלת)',t) or n<=2:
            print(f"  {l['base']:5.0f} {'B' if allb else ' '}{'C' if cen else ' '} {sz:4.1f} {l['x0']:3.0f}-{l['x1']:3.0f} | {t[:95]}")
