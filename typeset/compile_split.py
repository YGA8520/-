#!/usr/bin/env python3
"""Split an old-style compilation (table of contents with dotted leaders, 'בס"ד <author>' line before every title, optional
label lines 'סי׳ ד׳' / 'סעי׳ ז׳' before the centred title) into articles.  A generalisation of book.split_big with fuzzy title matching."""
import re, difflib
from ingest import load, doc_default_size
import book
from book import N, BASAD, classify_items, used_footnotes, honorific
from parse_docx import fix_quotes

LABEL_ANY = re.compile(r"^\s*(סי['׳]|סימן|סעי['׳]|סעיף|יורה דעה|או[\"״]ח)")


def _canon(s):
    s = N(s)
    s = s.replace('עניין', 'ענין').replace('ברכות', 'ברכת').replace('פחות', 'פחות').replace('בפחות', 'פחות')
    return s


def _close(a, b):
    a, b = _canon(a), _canon(b)
    if not a or not b:
        return False
    if a == b or (len(b) > 12 and a.startswith(b)) or (len(a) > 12 and b.startswith(a)):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.88


def split_compile(path, skip_prefix=('עלון שיעורו', 'שיעור בענין קריאת שם'), author_alias=None):
    author_alias = author_alias or {}
    items, fns = load(path)
    D = doc_default_size(items)
    toc, toc_end = [], 0
    for n, it in enumerate(items[:120]):
        if it['k'] == 'p' and re.search(r'\.{4,}', it['text']):
            toc.append(re.sub(r'\.{3,}.*', '', it['text']).strip())
            toc_end = n
    pos = toc_end + 1
    starts = []
    for t in toc:
        found = None
        if any(t.startswith(x) for x in skip_prefix):
            starts.append(None)
            continue
        for n in range(pos, len(items)):
            it = items[n]
            if it['k'] != 'p' or not it['text']:
                continue
            if _close(it['text'], t) and (it['align'] == 'center' or any(r.get('b') for r in it['runs'])):
                found = n
                break
        starts.append(found)
        if found is not None:
            pos = found + 1
    idxs = [(i, s) for i, s in enumerate(starts) if s is not None]
    out = []
    for k, (ti, s) in enumerate(idxs):
        e = idxs[k + 1][1] if k + 1 < len(idxs) else len(items)
        author, labs = None, []
        back = s - 1
        lo = idxs[k - 1][1] if k else toc_end
        while back > lo and back > s - 9:
            it = items[back]
            if it['k'] == 'p' and it['text']:
                if BASAD.match(it['text']) and author is None:
                    author = BASAD.sub('', it['text']).strip()
                elif LABEL_ANY.match(it['text']) and len(it['text']) < 40:
                    labs.insert(0, it['text'].strip())
            back -= 1
        body = items[s + 1:e]
        cut = len(body)
        while cut > 0:
            it = body[cut - 1]
            if it['k'] == 'p' and (not it['text'] or BASAD.match(it['text']) or LABEL_ANY.match(it['text']) and len(it['text']) < 40):
                cut -= 1
            else:
                break
        body = [it for it in body[:cut] if not (it['k'] == 'p' and BASAD.match(it['text']) and len(it['text']) < 60)]
        blocks, fn_out = classify_items(body, fns, D)
        a = author_alias.get(author, author or '')
        out.append({'title': fix_quotes(toc[ti].replace('׳', "'")), 'author_raw': author, 'author': a, 'labels': [fix_quotes(l) for l in labs],
                    'blocks': blocks, 'footnotes': used_footnotes(blocks, fn_out)})
    missing = [t for t, s in zip(toc, starts) if s is None and not any(t.startswith(x) for x in skip_prefix)]
    return out, missing
