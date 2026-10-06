import json, re, sys
P=json.load(open('work/lines.json'))
def fmt(p):
    W=p['w']; out=[]
    rows=[]
    for l in p['lines']:
        t=''.join(r['t'] for r in l['runs']).strip()
        if not t: continue
        cx=(l['x0']+l['x1'])/2
        wd=l['x1']-l['x0']
        flags=''
        if re.fullmatch(r'[_\s\-]+',t): rows.append(('LINE',l)); continue
        allb=all(r['b'] for r in l['runs'] if r['t'].strip())
        anyb=any(r['b'] for r in l['runs'] if r['t'].strip())
        if allb: flags+='B'
        elif anyb: flags+='b'
        if abs(cx-W/2)<14 and wd<W*0.75: flags+='C'
        sizes=sorted({r['s'] for r in l['runs'] if r['t'].strip()})
        # underlined?
        if any(r['u'] for r in l['runs'] if r['t'].strip()): flags+='U'
        # mark inline small/bold segments
        parts=[]
        for r in l['runs']:
            tt=r['t']
            if r['b'] and not allb: tt='**'+tt.strip()+'** '
            parts.append(tt)
        rows.append((flags,l,''.join(parts).strip(),sizes))
    res=[]; i=0
    while i<len(rows):
        r=rows[i]
        if r[0]=='LINE':
            j=i
            while j<len(rows) and rows[j][0]=='LINE': j+=1
            res.append(f'      [lines x{j-i}]'); i=j; continue
        flags,l,t,sizes=r
        res.append(f"{l['base']:6.1f} {l['x0']:5.0f}-{l['x1']:3.0f} {','.join(str(s) for s in sizes):9s} {flags:3s}| {t}")
        i+=1
    return res
a=int(sys.argv[1]); b=int(sys.argv[2])
for p in P:
    if a<=p['n']<=b:
        print(f"===== PAGE {p['n']} =====")
        print('\n'.join(fmt(p)))
