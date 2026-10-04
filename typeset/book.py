#!/usr/bin/env python3
"""Assemble the whole booklet (doc.json) from the source .docx files.

  * the big compilation (f17) is split into its articles using its own table of contents
  * the additional single-article files are added in their place (by siman)
  * files that are fully contained in the compilation are skipped (dedupe)
"""
import json, os, re, sys, collections
from ingest import load, doc_default_size
from parse_docx import normalize_runs, mark_sources, all_bold, as_heading_runs, runs_text, fix_quotes, SECTION

SRC = os.environ.get('SRC_DIR', '/tmp/claude-0/-home-user--/e48d2585-9ec4-5df3-ad1f-53def33d6015/scratchpad/src')
GER, GERSH = '׳', '״'


def N(s):
    return ''.join(re.findall(r'[א-ת]', s))


def heb_label(s):
    """סי' ד' / סימן סא סעיף ג -> סימן ד׳ ..."""
    s = fix_quotes(s.replace('סי׳', 'סימן').replace("סי'", 'סימן'))
    return s.strip()


def honorific(name):
    name = re.sub(r'\s+', ' ', name.replace('\t', ' ')).strip()
    name = name.replace('פריבשטיין', 'פרבשטיין').replace('נהור', 'נאור')
    name = fix_quotes(name)
    if not name:
        return name
    if name.endswith('שליט' + GERSH + 'א'):
        return name
    return name + ' שליט' + GERSH + 'א'


def attach_after_first_word(runs, fnruns):
    out, done = [], False
    for r in runs:
        if not done and 'fn' not in r and ' ' in r['t'].strip():
            i = r['t'].index(' ', len(r['t']) - len(r['t'].lstrip()))
            a, b = dict(r), dict(r)
            a['t'], b['t'] = r['t'][:i], r['t'][i:]
            out.append(a)
            out.extend(fnruns)
            out.append(b)
            done = True
        else:
            out.append(r)
    if not done:
        out.extend(fnruns)
    return out


# ------------------------------------------------------------------ paragraph preparation
def prep_runs(runs, D, small_ratio=0.8):
    out = []
    for r in runs:
        r = dict(r)
        sz = r.pop('sz', None)
        if 'fn' not in r and D and sz and sz <= D * small_ratio:
            r['sm'] = True
        out.append(r)
    return out


def classify_items(items, fns, D, title_norm=None):
    """items: ingest items for ONE article body -> blocks."""
    # explicit small runs present?
    small_chars = sum(len(r['t']) for it in items if it['k'] == 'p' for r in it['runs'] if D and r.get('sz') and r['sz'] <= D * 0.8)
    heuristic = small_chars < 40
    blocks = []
    pending_fn = []
    for it in items:
        if it['k'] == 'tbl':
            rows = []
            for ri, row in enumerate(it['rows']):
                cells = []
                for cell in row:
                    rr = normalize_runs(prep_runs(cell, D))
                    if ri == 0:
                        for r in rr:
                            if 'fn' not in r:
                                r['b'] = True
                    cells.append(rr)
                rows.append(cells)
            blocks.append({'t': 'tbl', 'rows': rows})
            continue
        if it.get('img'):
            continue
        runs = normalize_runs(prep_runs(it['runs'], D))
        if not runs or (not runs_text(runs).strip() and not any('fn' in r for r in runs)):
            continue
        if not runs_text(runs).strip():          # only footnote references (e.g. an asterisk on the title): move to the next paragraph
            pending_fn.extend([r for r in runs if 'fn' in r])
            continue
        if pending_fn:
            runs = attach_after_first_word(runs, pending_fn)
            pending_fn = []
        text = runs_text(runs).strip()
        n = len(text)
        align = it['align']
        if re.fullmatch(r"[\u05d0-\u05ea]{1,2}[׳'.:]?", text):      # a lone section letter ("א", "ב") -> small centred heading
            blocks.append({'t': 'h3', 'runs': [{'t': text.rstrip('.:'), 'b': True}]})
            continue
        if all_bold(runs) and (align == 'center' or n <= 140):
            m = SECTION.match(text.replace(GER, "'"))
            if m and not any('fn' in r for r in runs):
                blocks.append({'t': 'h2', 'runs': [{'t': ('%s %s' % (m.group(1), m.group(2))).replace("'", GER).strip()}]})
                rest = m.group(3).strip()
                if rest:
                    blocks.append({'t': 'h3', 'runs': [{'t': rest.rstrip('.'), 'b': True}]})
            else:
                blocks.append({'t': 'h3', 'runs': as_heading_runs(runs)})
            continue
        if all_bold(runs):
            blocks.append({'t': 'h3', 'runs': as_heading_runs(runs)})
            continue
        blocks.append({'t': 'p', 'runs': mark_sources(runs, heuristic=heuristic)})
    # footnotes
    fnout = {}
    for k, v in fns.items():
        rr = mark_sources(normalize_runs(prep_runs(v, D)), heuristic=heuristic)
        # footnote text is not bold unless it is entirely bold -> drop incidental bold
        for r in rr:
            r.pop('b', None)
        if rr and 'fn' not in rr[0]:
            rr[0]['t'] = re.sub(r'^\*\s*', '', rr[0]['t'])
        if rr:
            fnout[k] = rr
    return blocks, fnout


def used_footnotes(blocks, fns):
    ids = set()
    for b in blocks:
        if b['t'] == 'tbl':
            continue
        for r in b['runs']:
            if 'fn' in r:
                ids.add(r['fn'])
    return {k: v for k, v in fns.items() if k in ids}


# ------------------------------------------------------------------ f17: split by its table of contents
BASAD = re.compile(r'^\s*בס["״]ד\b')
LABEL = re.compile(r"^סי['׳]\s*")

TITLE_ALT = {  # toc title -> text actually found in the body
    'החובה להתאמץ בדור אחרון': 'החובה להתאמץ בתפילה בדור האחרון',
    'סוגיית נטילת ידיים': 'סוגיא דנטילת ידים שחרית',
}
SKIP_TOC = ('עלון שיעורו',)


def split_big(path='f17.docx'):
    items, fns = load(os.path.join(SRC, path))
    D = doc_default_size(items)
    toc, toc_end = [], 0
    for n, it in enumerate(items[:80]):
        if it['k'] == 'p' and re.search(r'\.{4,}', it['text']):
            toc.append(re.sub(r'\.{3,}.*', '', it['text']).strip())
            toc_end = n
    pos = toc_end + 1
    starts = []
    for t in toc:
        if any(t.startswith(x) for x in SKIP_TOC):
            starts.append(None)
            continue
        nt = N(TITLE_ALT.get(t, t))
        found = None
        for n in range(pos, len(items)):
            it = items[n]
            if it['k'] != 'p':
                continue
            x = N(it['text'])
            if x and (x == nt or (len(nt) > 12 and x.startswith(nt))) and any(r.get('b') for r in it['runs']):
                found = n
                break
        if found is None:
            raise SystemExit('title not found in body: ' + t)
        starts.append(found)
        pos = found + 1
    arts = []
    label = None
    idxs = [(i, s) for i, s in enumerate(starts) if s is not None]
    for k, (ti, s) in enumerate(idxs):
        e = idxs[k + 1][1] if k + 1 < len(idxs) else len(items)
        # the article's own head: author line + optional label right before the title
        author, lab = None, None
        back = s - 1
        while back > (idxs[k - 1][1] if k else toc_end) and back > s - 8:
            it = items[back]
            if it['k'] == 'p' and it['text']:
                if BASAD.match(it['text']) and author is None:
                    author = BASAD.sub('', it['text']).strip()
                elif LABEL.match(it['text']) and lab is None:
                    lab = it['text']
            back -= 1
        if lab:
            label = heb_label(lab)
        # trailing head of the NEXT article (basad+author, label) belongs to the next article -> trim from this body
        body_items = items[s + 1:e]
        cut = len(body_items)
        while cut > 0:
            it = body_items[cut - 1]
            if it['k'] == 'p' and (not it['text'] or BASAD.match(it['text']) or LABEL.match(it['text'])):
                cut -= 1
            else:
                break
        body_items = body_items[:cut]
        # page-artifact lines in the middle of the article
        clean = []
        for it in body_items:
            if it['k'] == 'p' and BASAD.match(it['text']) and len(it['text']) < 60:
                continue
            clean.append(it)
        blocks, fn_out = classify_items(clean, fns, D)
        arts.append({
            'src': 'f17', 'order': k, 'title': fix_quotes(toc[ti].replace('׳', "'")), 'author': honorific(author or ''), 'label': label,
            'blocks': blocks, 'footnotes': used_footnotes(blocks, fn_out),
        })
    return arts


# ------------------------------------------------------------------ additional single-article files
EXTRA = [
    # file, skip_first (non-empty head paragraphs), title, label, author, subtitle, sort key (siman number, sub)
    dict(file='f02.docx', skip=2, title='בענין נטילת ידיים של שחרית', subtitle='שיעורי חבורת ברומו של עולם (בקצרה)', label="סימן ד'", author='מכלל האברכים', siman=4, after=True),
    dict(file='f03.docx', skip=1, title='בענין ברכת אשר יצר', label="סימן ו'", author='הרב נאור רוזין', siman=6, after=True),
    dict(file='f10.docx', skip=1, title='בענין ברכות קר"ש', label='סימן נא', author='הרב נאור רוזין', siman=51),
    dict(file='f14.docx', skip=2, title='גדר רואין זה את זה בצירוף עשרה למנין', label="סימן נה סעיף ט\"ז", author="נשיא הכולל הגאון ר' דוד פוטאש", siman=55),
    dict(file='f12.docx', skip=2, title='ענין הכוונה בקר"ש וענין המסירות נפש בקר"ש', label="סימן סא סעיפים א׳–ב׳", author='הרב נאור רוזין', siman=61, sub=1),
    dict(file='f11.docx', skip=1, title='בענין אמירת ברוך שם כבוד מלכותו לעולם ועד', label="סימן סא סעיף ג׳", author='הרב נאור רוזין', siman=61, sub=2),
    dict(file='f13.docx', skip=1, title='בענין כפילת שמע שמע', label="סימן סא סעיף ט׳", author='הרב נאור רוזין', siman=61, sub=3),
    dict(file='f15.docx', skip=2, title='בענין תפלה וקר"ש בכל לשון', label="סימן סב סעיף ב׳", author='הרב נאור רוזין', siman=62),
    dict(file='f16.docx', skip=3, title='ספירת העומר מן התורה או מדרבנן', label='סימן תפ"ט', author='הרב נח קליין', siman=489),
]


def load_extra(m):
    items, fns = load(os.path.join(SRC, m['file']))
    D = doc_default_size(items)
    k = 0
    body = []
    for it in items:
        if it['k'] == 'p' and (not it['text'] or it.get('img')):
            continue                      # empty paragraphs and pictures (logo) are dropped and do not count
        if it['k'] == 'p' and k < m['skip']:
            k += 1
            continue
        body.append(it)
    blocks, fn_out = classify_items(body, fns, D)
    return {
        'src': m['file'], 'title': fix_quotes(m['title']), 'subtitle': m.get('subtitle'), 'author': honorific(m['author']) if m['author'] != 'מכלל האברכים' else m['author'],
        'label': fix_quotes(m['label']), 'blocks': blocks, 'footnotes': used_footnotes(blocks, fn_out), 'siman': m['siman'], 'sub': m.get('sub', 0),
        'after': m.get('after', False),
    }


SIMAN_NUM = {'ד': 4, 'ה': 5, 'ו': 6, 'מו': 46, 'מז': 47, 'נא': 51, 'נה': 55, 'סא': 61, 'סב': 62, 'תפט': 489}


def siman_of(label):
    m = re.match(r'סימן\s+([א-ת׳״"\']+)', label or '')
    return SIMAN_NUM.get(N(m.group(1)), 0) if m else 0


def build():
    big = split_big()
    for a in big:
        a['siman'] = siman_of(a['label'])
    extras = [load_extra(m) for m in EXTRA]
    # merge: extras go after the last big article of the same siman (or by order of siman)
    ordered = list(big)
    for ex in sorted(extras, key=lambda x: (x['siman'], x['sub'])):
        # position: after last article with siman <= ex.siman  (stable)
        pos = 0
        for i, a in enumerate(ordered):
            if a['siman'] <= ex['siman'] and a['siman'] != 0:
                pos = i + 1
        ordered.insert(pos, ex)
    return ordered


if __name__ == '__main__':
    arts = build()
    out = sys.argv[1] if len(sys.argv) > 1 else 'book.doc.json'
    doc = {'book': {'name': 'פלפולא דאורייתא', 'subtitle': 'קובץ חבורא מאברכי כולל ברומו של עולם'}, 'firstPageNumber': 1, 'articles': arts}
    json.dump(doc, open(out, 'w'), ensure_ascii=False)
    tot = 0
    for i, a in enumerate(arts, 1):
        w = sum(len(runs_text(b['runs']).split()) for b in a['blocks'] if b['t'] != 'tbl')
        tot += w
        print(f"{i:2d} {a['src']:8s} {a.get('label') or '':22s} | {a['title'][:44]:44s} | {a['author'][:28]:28s} | blocks {len(a['blocks']):3d} fn {len(a['footnotes']):2d} words {w}")
    print('total words', tot)
