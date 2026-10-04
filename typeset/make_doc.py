#!/usr/bin/env python3
"""Build doc.json (content model for engine.js) from the manifest of source files."""
import json, sys, os, re
from parse_docx import parse_docx, classify

SRC = '/tmp/claude-0/-home-user--/e48d2585-9ec4-5df3-ad1f-53def33d6015/scratchpad/src'

SAMPLE = [
    dict(file='f04.docx', label='סימן ה׳', title='בדין כוונה בשמות הקדושים', short='בדין כוונה בשמות הקדושים',
         author='הרב אליהו פרבשטיין', basad='בס״ד'),
]


def build(manifest, out):
    arts = []
    for m in manifest:
        paras, fns = parse_docx(os.path.join(SRC, m['file']))
        blocks, head = classify(paras)
        # drop heading-like block that duplicates the title
        arts.append({
            'label': m.get('label'), 'title': m['title'], 'shortTitle': m.get('short', m['title']),
            'author': m.get('author'), 'basad': m.get('basad'), 'abstract': m.get('abstract'),
            'blocks': blocks, 'footnotes': fns,
        })
    doc = {'book': {'name': 'פלפולא דאורייתא'}, 'firstPageNumber': 1, 'articles': arts}
    json.dump(doc, open(out, 'w'), ensure_ascii=False)
    print('articles', len(arts), 'blocks', sum(len(a['blocks']) for a in arts))


if __name__ == '__main__':
    build(SAMPLE, sys.argv[1] if len(sys.argv) > 1 else 'sample.doc.json')
