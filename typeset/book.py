#!/usr/bin/env python3
"""Assemble the whole booklet (doc.json) from the source .docx files.

  * the big compilation (f17) is split into its articles using its own table of contents
  * the additional single-article files are added in their place (by siman)
  * files that are fully contained in the compilation are skipped (dedupe)
"""
import json, os, re, sys, collections, unicodedata
from ingest import load, doc_default_size
from parse_docx import normalize_runs, mark_sources, all_bold, as_heading_runs, runs_text, fix_quotes, fix_space_before_punct, SECTION

HERE = os.path.dirname(os.path.abspath(__file__))
# folder with the source .docx files: $SRC_DIR, or ./src, or (cloud session) the scratchpad copy
SRC = os.environ.get('SRC_DIR') or next((d for d in (os.path.join(HERE, 'src'), '/tmp/claude-0/-home-user--/e48d2585-9ec4-5df3-ad1f-53def33d6015/scratchpad/src') if os.path.isdir(d)), os.path.join(HERE, 'src'))
FILE_NAMES = json.load(open(os.path.join(HERE, 'src_names.json'), encoding='utf-8'))   # fNN.docx -> the original file name


def src_path(name):
    """the source file by its short name (f17.docx) or by the original name as uploaded (Hebrew names, Unicode-normalisation tolerant)"""
    nf = lambda x: unicodedata.normalize('NFC', x).replace('\u200e', '').replace('\u200f', '').strip()
    if not os.path.isdir(SRC):
        raise SystemExit('source folder not found: %s  (set SRC_DIR to the folder with the .docx files)' % SRC)
    have = {nf(f): f for f in os.listdir(SRC)}
    for cand in (name, FILE_NAMES.get(name, '')):
        if cand and nf(cand) in have:
            return os.path.join(SRC, have[nf(cand)])
    raise SystemExit('source file missing: %s (original name: %s) in %s' % (name, FILE_NAMES.get(name), SRC))
GER, GERSH = '׳', '״'


def N(s):
    return ''.join(re.findall(r'[א-ת]', s))


def heb_label(s):
    """סי' ד' / סימן סא סעיף ג -> סימן ד׳ ..."""
    s = fix_quotes(s.replace('סי׳', 'סימן').replace("סי'", 'סימן'))
    return s.strip()


TITLE_WORDS = ('הרב', 'הרה״ג', 'הרה"ג', 'הגאון', 'נשיא', 'האברך', 'האה״ח', 'האה"ח', 'ר׳', "ר'", 'מכלל', 'שיעורו')


LEADERS = [   # in the order they appear inside a siman: (core name, the title printed with it)
    (re.compile(r'מרדכי\s+פוטא?ש'), "נשיא הכולל הגאון ר׳ מרדכי פוטש שליט״א"),
    (re.compile(r'דוד\s+פוטא?ש'), "נשיא הכולל הגאון ר׳ דוד פוטש שליט״א"),
    (re.compile(r'משה\s+זאדה'), "ראש הכולל הרב ר׳ משה זאדה שליט״א"),
]


def author_rank(author):
    """0 מרדכי פוטש, 1 דוד פוטש, 2 משה זאדה, 3 everybody else (the order of the חבורות inside every siman)"""
    for k, (rx, _) in enumerate(LEADERS):
        if rx.search(author or ''):
            return k
    return len(LEADERS)


def honorific(name):
    """"הרב" in front of an author who has no title yet, "שליט״א" after the name"""
    name = re.sub(r'\s+', ' ', name.replace('\t', ' ')).strip()
    name = name.replace('פריבשטיין', 'פרבשטיין').replace('נהור', 'נאור')
    name = fix_quotes(name)
    if not name:
        return name
    for rx, full in LEADERS:
        if rx.search(name):
            return full
    if not name.startswith(TITLE_WORDS):
        name = 'הרב ' + name
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


HEAD_START = re.compile(r'^(שיטת|שיטות|דעת|פסק|חידושי|תשובת|ביאור|דברי)\s')


CONTEXT_HEADINGS = {      # lines typed as plain text that are headings only by context (title of a quoted source / section)
    N('ראב״ד - תשובות ופסקים סימן מד'), N('משנ״ב ובה״ל'), N('ב״ח ופרישה'), N('בענין הרנ״ב תיבות לאשה'), N('יש לדון'), N('באר שבע מסכת סוטה דף לב עמוד א'), N('שו״ת משנה הלכות חלק ג סימן פג'), N('תפלה בכל לשון'),
}


# a sentence that continues the argument (starts with ו / הנה / אמנם ...) or a very long text is not a sub-heading even if it is bold
SENTENCE_HEAD = re.compile(r'^(?:[א-ת]{1,2}\.\s*)?(?:ו(?!בענין|בעניין|בדין|ביאור|לענין|לעניין)|הנה\b|אמנם\b|אבל\b|מהא\b|לפי זה\b|להלכה\b)')


def is_sentence_heading(text):
    words = len(text.split())
    return words >= 30 or (words >= 5 and bool(SENTENCE_HEAD.match(text)))


def classify_items(items, fns, D, title_norm=None, loose_heads=False):
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
        force_para = is_sentence_heading(text)
        if force_para:                          # ordinary paragraph (bold lead word as everywhere), not a heading and not all bold
            runs = [{k: v for k, v in r.items() if k != 'b'} for r in runs]
        # headings the author marked with a Word heading style, or with underline only (short line, every letter underlined)
        letters = sum(len(re.findall(r'[\u05d0-\u05ea]', r['t'])) for r in it['runs'] if 'fn' not in r)
        ul_letters = sum(len(re.findall(r'[\u05d0-\u05ea]', r['t'])) for r in it['runs'] if 'fn' not in r and r.get('u'))
        style_head = it['style'].lower().startswith('heading') or it['style'].startswith('כותרת')
        underline_head = n <= 110 and letters >= 3 and ul_letters >= 0.85 * letters
        context_head = N(text) in CONTEXT_HEADINGS and n <= 60
        # (single-article files) a short centred line that is not bold, or a short "שיטת X." style line, is a sub-heading as well
        loose_head = loose_heads and not any('fn' in r for r in runs) and (
            (align == 'center' and n <= 100 and len(text.split()) <= 12) or
            (len(text.split()) <= 7 and n <= 60 and HEAD_START.match(text) and not text.rstrip().endswith(',')))
        if not force_para and ((style_head and n <= 220) or underline_head or context_head or loose_head):
            m = SECTION.match(text.replace(GER, "'"))
            if m and not any('fn' in r for r in runs):
                blocks.append({'t': 'h2', 'runs': [{'t': ('%s %s' % (m.group(1), m.group(2))).replace("'", GER).strip()}]})
                if m.group(3).strip():
                    blocks.append({'t': 'h3', 'runs': [{'t': m.group(3).strip().rstrip('.'), 'b': True}]})
            else:
                blocks.append({'t': 'h3', 'runs': as_heading_runs(runs)})
            continue
        if not force_para and re.fullmatch(r"[\u05d0-\u05ea]{1,2}[׳'.:]?", text):      # a lone section letter ("א", "ב") -> small centred heading
            blocks.append({'t': 'h3', 'runs': [{'t': text.rstrip('.:'), 'b': True}]})
            continue
        if not force_para and all_bold(runs) and (align == 'center' or n <= 140):
            m = SECTION.match(text.replace(GER, "'"))
            if m and not any('fn' in r for r in runs):
                blocks.append({'t': 'h2', 'runs': [{'t': ('%s %s' % (m.group(1), m.group(2))).replace("'", GER).strip()}]})
                rest = m.group(3).strip()
                if rest:
                    blocks.append({'t': 'h3', 'runs': [{'t': rest.rstrip('.'), 'b': True}]})
            else:
                blocks.append({'t': 'h3', 'runs': as_heading_runs(runs)})
            continue
        if all_bold(runs):   # a long bold paragraph that is not centred is the author's emphasis, not a heading: keep it a paragraph
            blocks.append({'t': 'p', 'runs': mark_sources([dict(r) for r in runs], heuristic=heuristic)})
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
    items, fns = load(src_path(path))
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
    dict(file='f14.docx', skip=2, title='גדר רואין זה את זה בצירוף עשרה למנין', label="סימן נה סעיף ט\"ז", author="נשיא הכולל הגאון ר' דוד פוטאש", siman=55, seif=16),
    dict(file='f12.docx', skip=2, title='ענין הכוונה בקר"ש וענין המסירות נפש בקר"ש', label="סימן סא סעיפים א׳–ב׳", author='הרב נאור רוזין', siman=61, sub=1, seif=1),
    dict(file='f11.docx', skip=1, title='בענין אמירת ברוך שם כבוד מלכותו לעולם ועד', label="סימן סא סעיף ג׳", author='הרב נאור רוזין', siman=61, sub=2, seif=3),
    dict(file='f13.docx', skip=1, title='בענין כפילת שמע שמע', label="סימן סא סעיף ט׳", author='הרב נאור רוזין', siman=61, sub=3, seif=9),
    dict(file='f15.docx', skip=2, title='בענין תפלה וקר"ש בכל לשון', label="סימן סב סעיף ב׳", author='הרב נאור רוזין', siman=62, seif=2),
    dict(file='f16.docx', skip=3, title='ספירת העומר מן התורה או מדרבנן', label='סימן תפ"ט', author='הרב נח קליין', siman=489),
]


def load_extra(m):
    items, fns = load(src_path(m['file']))
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


SHORT_TITLES = {   # N(title prefix) -> text for the running head
    N('בביאור האיסור הוצאת שם שמים ללא כוונה'): 'בביאור האיסור הוצאת שם שמים ללא כוונה',
}


def build():
    big = split_big()
    for k, a in enumerate(big):
        a['siman'] = siman_of(a['label'])
        a['seif'], a['idx'] = 0, k
    extras = [load_extra(m) for m in EXTRA]
    for k, (m, ex) in enumerate(zip(EXTRA, extras)):
        ex['seif'], ex['idx'] = m.get('seif', 0), 1000 + k
    allarts = big + extras
    try:                                    # the additional חבורות (folder "חבורות"), see new_articles.py
        import new_articles
        allarts += new_articles.build_articles()
    except SystemExit as e:
        print('WARNING: additional חבורות not added:', e)
    # order: by siman; inside a siman: מרדכי פוטש, דוד פוטש, משה זאדה, then everybody else; then se'if, then the order they came in
    ordered = sorted(allarts, key=lambda a: (a['siman'] or 0, author_rank(a['author']), a['seif'], a['idx']))
    for a in ordered:                       # running-head versions of long titles (no ellipsis; the client wants a clean cut)
        for pre, short in SHORT_TITLES.items():
            if N(a['title']).startswith(pre):
                a['shortTitle'] = short
    # typing slips: a space in front of , . ; :
    for a in ordered:
        for blk in a['blocks']:
            if blk['t'] == 'tbl':
                for row in blk['rows']:
                    for cell in row:
                        fix_space_before_punct(cell)
            else:
                fix_space_before_punct(blk['runs'])
        for runs in a['footnotes'].values():
            fix_space_before_punct(runs)
    # internal divider page wherever the siman changes (label of the first article of the group)
    cur = 0
    for a in ordered:
        a['divider'] = None
        if a['siman'] and a['siman'] != cur:
            a['divider'] = re.split(r'\s+סעי', a['label'])[0]
            cur = a['siman']
    if ordered and not ordered[0]['siman']:           # the articles that precede siman 1: the introductions to the booklet
        ordered[0]['divider'] = 'פתיחות'
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
