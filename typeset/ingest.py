#!/usr/bin/env python3
"""Reads the source .docx files in document order (paragraphs + tables) into plain dicts."""
import re, collections
import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree
from parse_docx import normalize_runs, fix_quotes, clean_ws


def _val(el, tag):
    e = el.find(qn(tag)) if el is not None else None
    return None if e is None else e.get(qn('w:val'))


def read_runs_sz(p_el):
    """runs with bold / size / footnote refs (size in pt or None)."""
    out = []
    for r in p_el.iter(qn('w:r')):
        rpr = r.find(qn('w:rPr'))
        fr = r.find(qn('w:footnoteReference'))
        if fr is not None:
            out.append({'t': '', 'fn': fr.get(qn('w:id'))})
            continue
        b = rpr is not None and (rpr.find(qn('w:b')) is not None and rpr.find(qn('w:b')).get(qn('w:val')) not in ('0', 'false'))
        sz = rpr.find(qn('w:sz')) if rpr is not None else None
        sz = int(sz.get(qn('w:val'))) / 2 if sz is not None else None
        t = ''
        for x in r:
            if x.tag == qn('w:t'):
                t += x.text or ''
            elif x.tag in (qn('w:tab'), qn('w:br')):
                t += ' '
        if t:
            u = rpr is not None and rpr.find(qn('w:u')) is not None and rpr.find(qn('w:u')).get(qn('w:val')) not in ('none',)
            ital = rpr is not None and rpr.find(qn('w:i')) is not None and rpr.find(qn('w:i')).get(qn('w:val')) not in ('0', 'false')
            out.append({'t': t, 'b': bool(b), 'sz': sz, 'u': bool(u), 'i': bool(ital)})
    return out


def load(path):
    d = docx.Document(path)
    items = []
    for ch in d.element.body.iterchildren():
        if ch.tag == qn('w:p'):
            par = Paragraph(ch, d)
            runs = read_runs_sz(ch)
            jc = _val(ch.find(qn('w:pPr')), 'w:jc')
            has_img = bool(ch.findall('.//' + qn('w:drawing')) or ch.findall('.//' + qn('w:pict')))
            items.append({'k': 'p', 'runs': runs, 'align': jc, 'style': par.style.name, 'img': has_img,
                          'text': ''.join(r['t'] for r in runs).strip()})
        elif ch.tag == qn('w:tbl'):
            rows = []
            for tr in ch.findall(qn('w:tr')):
                row = []
                for tc in tr.findall(qn('w:tc')):
                    cell = []
                    for p in tc.findall(qn('w:p')):
                        rr = read_runs_sz(p)
                        if rr:
                            if cell:
                                cell.append({'t': ' ', 'b': False})
                            cell.extend(rr)
                    row.append(cell)
                rows.append(row)
            items.append({'k': 'tbl', 'rows': rows, 'text': ''})
    fns = {}
    for rel in d.part.rels.values():
        if rel.reltype.endswith('/footnotes'):
            root = etree.fromstring(rel.target_part.blob)
            for fn in root.findall(qn('w:footnote')):
                fid = fn.get(qn('w:id'))
                if fid in ('-1', '0'):
                    continue
                runs = []
                for k, p in enumerate(fn.findall(qn('w:p'))):
                    rr = [r for r in read_runs_sz(p) if 'fn' not in r]
                    if rr and runs:
                        runs.append({'t': ' ', 'b': False})
                    runs.extend(rr)
                if ''.join(r['t'] for r in runs).strip():
                    fns[fid] = runs
    return items, fns


def doc_default_size(items):
    c = collections.Counter()
    for it in items:
        if it['k'] == 'p':
            for r in it['runs']:
                if r.get('sz'):
                    c[r['sz']] += len(r['t'])
    return c.most_common(1)[0][0] if c else None
