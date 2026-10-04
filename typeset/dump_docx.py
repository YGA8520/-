import sys, docx
from docx.oxml.ns import qn
from lxml import etree

def runs_of(p):
    out=[]
    for r in p._p.iter(qn('w:r')):
        t=''.join((x.text or '') if x.tag==qn('w:t') else ('\t' if x.tag==qn('w:tab') else ('\n' if x.tag==qn('w:br') else '')) for x in r)
        fr=r.find(qn('w:footnoteReference'))
        rpr=r.find(qn('w:rPr'))
        b = rpr is not None and rpr.find(qn('w:b')) is not None and rpr.find(qn('w:b')).get(qn('w:val')) not in ('0','false')
        sz = None
        if rpr is not None and rpr.find(qn('w:sz')) is not None: sz=int(rpr.find(qn('w:sz')).get(qn('w:val')))/2
        out.append((t, b, sz, fr.get(qn('w:id')) if fr is not None else None))
    return out

def render(p, show_sz=False):
    s=[]
    for t,b,sz,fn in runs_of(p):
        if fn is not None: s.append('[^%s]'%fn)
        if t: s.append('**%s**'%t if b else t)
    return ''.join(s)

if __name__=='__main__':
    d=docx.Document(sys.argv[1]); lim=int(sys.argv[2]) if len(sys.argv)>2 else 400
    for i,p in enumerate(d.paragraphs):
        if p.text.strip():
            al=p.alignment
            print(f'{i} [{p.style.name}|{al}]', render(p)[:lim])
    for rel in d.part.rels.values():
        if rel.reltype.endswith('/footnotes'):
            root=etree.fromstring(rel.target_part.blob)
            print('\nFOOTNOTES')
            for fn in root.findall(qn('w:footnote')):
                txt=''.join(t.text or '' for t in fn.iter(qn('w:t')))
                if txt.strip(): print(fn.get(qn('w:id')), txt[:lim])
