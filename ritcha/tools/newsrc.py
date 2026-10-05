"""Questions taken from the additional files (zips 1-3) -> list of source units.

Every unit is {src, siman|None, section|None, blocks}.  Nothing is judged duplicate here; merge.py does that.
"""
import re, zipfile, glob, os
from xml.etree import ElementTree as ET
from model import Para, strip_runs, name_blk, norm_siman, marker_prefix_len, heb_num, NS, W

BASE = 'newfiles'

def load(rel):
    z = zipfile.ZipFile(os.path.join(BASE, rel))
    root = ET.fromstring(z.read('word/document.xml'))
    out = []
    for idx, p in enumerate(root.find('w:body', NS).iter(W + 'p')):
        chars = []
        for r in p.iter(W + 'r'):
            rp = r.find('w:rPr', NS)
            on = lambda t: rp is not None and rp.find('w:' + t, NS) is not None and rp.find('w:' + t, NS).get(W + 'val') not in ('0', 'false')
            for t in r.findall('w:t', NS):
                for ch in (t.text or ''):
                    chars.append((ch, on('b'), on('i'), on('u')))
        out.append(Para(idx, chars, None))
    return out

NOTE_INLINE = re.compile(r'\s*\[((?:הערת[^\[\]]*)|(?:[^\[\]]*שליט"א[^\[\]]*))\]\.?\s*$')
NOTE_ONLY = re.compile(r'^\[(.*)\]\.?$')

def name_of(text, idx):
    return dict(kind='name', runs=[(text.strip().rstrip('.').strip(), {})], idx=idx)

def blocks_of(p, strip_kind=None):
    """question block (+ a name block when the paragraph ends with a [הערת …] note, or is one)"""
    t = p.text
    m0 = NOTE_ONLY.match(t)
    if m0 and ('הערת' in t or 'שליט"א' in t):
        return [name_of(m0.group(1), p.idx)]
    n = marker_prefix_len(p, strip_kind) if strip_kind else 0
    m = NOTE_INLINE.search(t)
    if m:
        return [dict(kind='q', runs=p.runs(strip=n, hi=m.start()), idx=p.idx), name_of(m.group(1), p.idx)]
    return [dict(kind='q', runs=p.runs(strip=n), idx=p.idx)]

def item_rows(P, rows, strip_kind=None, name=None, src_rows=(), extra=()):
    blocks = []
    for k, r in enumerate(rows):
        blocks += blocks_of(P[r], strip_kind if k == 0 else None)
    for r in src_rows:
        blocks.append(dict(kind='src', runs=P[r].runs(), idx=r))
    blocks += list(extra)
    if name: blocks.append(name_of(name, rows[0]))
    return blocks

UNITS = []
def U(src, siman, blocks, section=None):
    UNITS.append(dict(src=src, siman=siman, section=section, blocks=blocks))

def parse_marked(rel, src, start=0, end=None, default_siman=None):
    """docs laid out as: 'סימן X' / letter / text… / letter / text…"""
    P = load(rel); end = end if end is not None else len(P) - 1
    siman = default_siman; cur = None
    def flush():
        nonlocal cur
        if cur and cur['rows']:
            U(src, siman_of(cur), item_rows(P, cur['rows']))
        cur = None
    def siman_of(c): return c['siman']
    for i in range(start, end + 1):
        p = P[i]; t = p.text
        if not t: continue
        if re.match(r'^סימן\s', t) and len(t) < 30:
            flush(); siman = norm_siman(t.split(None, 1)[1]); continue
        if re.match(r'^[א-ת]{1,2}$', t):
            flush(); cur = dict(rows=[], siman=siman); continue
        if cur is None: continue
        cur['rows'].append(i)
    flush()
    return P

# ---------------------------------------------------------------- the published pair: סימן סה + סו (the example's own source)
parse_marked('z1/ריתחא דאורייתא סימן סה - סו.docx', 'z1 סה-סו (גיליון מודפס)')
# ---------------------------------------------------------------- סימן ח (4 questions, marker rows)
parse_marked('z1/ריתחא דאורייתא סימן ח.docx', 'z1 סימן ח')

# ---------------------------------------------------------------- zip 2
f = 'z2/__מסמך של Microsoft Word חדש (1).docx'; P = load(f)
for q, n, s in ((3, 4, 'מח'), (6, 7, 'מח'), (10, 11, 'מט'), (13, 14, 'מט')):
    U('z2 מסמך חדש (1)', s, [strip_runs(P[q], 'bare1'), name_blk(P[n])])

f = 'z2/__ריתחא - נשא.docx'; P = load(f)
for q, n, s in ((3, 4, 'נא'), (5, 6, 'נא'), (7, 8, 'נא'), (9 + 1, 11, 'נב'), (12, 13, 'נב'), (14, 15, 'נב')):
    U('z2 ריתחא נשא', s, [strip_runs(P[q], 'bare1'), name_blk(P[n])])

f = 'z2/אהרן לייב פריזנד זאדה.docx'; P = load(f); who = 'אהרן לייב פריזנד'
U('z2 אהרן לייב פריזנד', 'ח', [blk for blk in item_rows(P, [2])] + [name_of(who, 2)])
U('z2 אהרן לייב פריזנד', 'ח', item_rows(P, [3, 4]) + [name_of(who, 3)])
U('z2 אהרן לייב פריזנד', 'סו', item_rows(P, [6]) + [name_of(who, 6)])
U('z2 אהרן לייב פריזנד', 'ח', item_rows(P, [8, 9, 10, 11]) + [name_of(who, 8)])
U('z2 אהרן לייב פריזנד', 'ח', item_rows(P, [13, 14]) + [name_of(who, 13)])

f = 'z2/זאדה ריתחא - מז.docx'; P = load(f)
U('z2 זאדה מז', 'מז', item_rows(P, [1, 2, 3], 'dot'))
U('z2 זאדה מז', 'מז', item_rows(P, [5, 6, 7, 8, 9], 'dot'))
U('z2 זאדה מז', 'מז', item_rows(P, [11, 12, 13], 'dot'))
U('z2 זאדה מז', 'מז', item_rows(P, [17, 18]))
U('z2 זאדה מז', 'מז', item_rows(P, [21, 22]))      # the block of notes that follows (rows 25-46) is NOT used

f = 'z2/סימן ו-ז אשר יצר.docx'; P = load(f)
for r in (4, 6, 8, 10): U('z2 סימן ו', 'ו', item_rows(P, [r]))

f = 'z2/ריתחא דאורייתא ב.docx'; P = load(f)
U('z2 ריתחא דאורייתא ב', 'סה', item_rows(P, [4]))
for r in (7, 10, 13, 18, 22): U('z2 ריתחא דאורייתא ב', 'סו', item_rows(P, [r]))

f = 'z2/ריתחא דאורייתא הלכות ציצית ק.docx'; P = load(f)
U('z2 הלכות ציצית', 'ח', item_rows(P, [2, 3, 4, 5, 6], 'num'))
U('z2 הלכות ציצית', 'ח', item_rows(P, [7], 'num'))
U('z2 הלכות ציצית', 'ח', item_rows(P, [9, 10, 11], 'num'))
U('z2 הלכות ציצית', 'ח', item_rows(P, [12], 'num'))
U('z2 הלכות ציצית', 'ח', item_rows(P, [13], 'num'))
U('z2 הלכות ציצית', 'ח', item_rows(P, [14, 15], 'num'))
U('z2 הלכות ציצית', 'ח', item_rows(P, [18, 19], 'num'))
U('z2 הלכות ציצית', 'כב', item_rows(P, [21, 22], 'num'))
U('z2 הלכות ציצית', 'כב', item_rows(P, [23], 'num'))
U('z2 הלכות ציצית', 'כא', item_rows(P, [25]))
U('z2 הלכות ציצית', 'כד', item_rows(P, [27], 'num'))
U('z2 הלכות ציצית', 'סו', item_rows(P, [33]))
U('z2 הלכות ציצית', 'סז', item_rows(P, [35]))

# ---------------------------------------------------------------- zip 3
P = load('z3/ריתחא דאורייתא סימן סו.docx')
p0 = P[0]; n0 = len('ריתחא דאורייתא סימן סו:')
U('z3 סימן סו', 'סו', [dict(kind='q', runs=p0.runs(strip=n0), idx=0)])
for r in (1, 2, 3): U('z3 סימן סו', 'סו', item_rows(P, [r]))

P = load('z3/ריתחא דאורייתא.docx')           # ברכת התורה / "מדוע לשיטת רב" – belongs to סימן מז
U('z3 ריתחא (מז)', 'מז', item_rows(P, [2, 3], 'dot'))
for r in (4, 5, 6, 7): U('z3 ריתחא (מז)', 'מז', item_rows(P, [r], 'dot'))

P = load('z3/ריתחא סימן ח.docx')
for r in (1, 2, 3, 4): U('z3 ריתחא סימן ח', 'ח', item_rows(P, [r]))

P = load('z3/ריתחא סימן סד.docx')
U('z3 ריתחא סימן סד', 'סד', item_rows(P, [5]))

P = load('z3/ריתחא.docx')
for q, n in ((3, 4), (5, 6), (7, 8), (9, 10), (11, 12)):
    U('z3 ריתחא במדבר', 'נא', [strip_runs(P[q], 'bare1'), name_blk(P[n])])

P = load('z3/שאלה הנוטל ידיו שחרית (1).docx')
for r in range(4, 33, 2): U('z3 נטילת ידים', 'ד', item_rows(P, [r]))

P = load('z3/שאלו לחידודא - מז.docx')
for r in (1, 2, 3, 4): U('z3 שאלות לחידודא', 'מז', item_rows(P, [r], 'dot'))
U('z3 שאלות לחידודא', 'מז', item_rows(P, [7], 'dot'))
for q, a in ((8, 9), (10, 11), (12, 13)):
    U('z3 שאלות לחידודא', 'מז', item_rows(P, [q, a], None) if False else
      [strip_runs(P[q], 'dot'), dict(kind='q', runs=P[a].runs(), idx=a)])

P = load('z3/שאלות בעניני תפלה וקריאת שמע.docx')
for r in range(0, 8): U('z3 תפילה וקריאת שמע', None, item_rows(P, [r]), section='שאלות שונות בעניני תפילה')

P = load('z3/שאלות וחידונים סימן קכג.docx')
U('z3 קכג', 'קכג', [dict(kind='q', runs=P[2].runs(), idx=2)] +
  [dict(kind='sub', label=heb_num(i - 2), runs=P[i].runs(), idx=i) for i in range(3, 9)])

P = load('z3/שאלות לסימן ה (2).docx')
U('z3 שאלות ה (2)', 'ה', item_rows(P, [5], None) + [name_of('הרב אהרן לייב פריזנד', 5)])
for r in (8, 10, 12, 14): U('z3 שאלות ה (2)', 'ה', item_rows(P, [r]) + [name_of('הרב נחום לוי', r)])
U('z3 שאלות ה (2)', 'ה', item_rows(P, [17, 18, 19]) + [name_of('הרב יהודה בהר', 17)])

P = load('z3/שאלות סימן ה (1).docx')
for r in range(4, 23, 2): U('z3 שאלות ה (1)', 'ה', item_rows(P, [r]))

P = load('z3/שאלות שונות בעניני תפלה.docx')
for r in (4, 6, 8, 10, 12, 14): U('z3 שאלות שונות', None, item_rows(P, [r]), section='שאלות שונות בעניני תפילה')

# ---------------------------------------------------------------- only in a PDF (no Word source) – read from the page images
PDF_AY = [
    'הרהור בדברי תורה בארבע אמות לקבר?',
    'לקרא קריאת שמע בתוך ארבע אמות לקבר של נפל או של שוטה?',
    'ברכת הרעמים והברקים בארבע אמות לקבר (מצוה עוברת)?',
    'אמירת תפילת הדרך בנסיעה ברכב עם מת?',
    'לקרא קריאת שמע ולהתפלל ליד קבר צדיק בתוך בית הקברות כללי?',
    'לקרא קריאת שמע ולהתפלל ליד קברי צדיקים והטעם?',
    'לומר קדיש ותהלים לעילוי נשמת ליד קבר והטעם?',
    'אונן במטוס אם חייב בקריאת שמע במטוס?',
    'בזמנינו שמוסרים המת לחברה קדישא אם אונן יאמר קריאת שמע ויתפלל?',
]
for k, t in enumerate(PDF_AY):
    b = [dict(kind='q', runs=[(t, {})], idx=-1)]
    if k == 8: b.append(name_of('בני החבורה', -1))
    U('PDF סימן עא (עא1)', 'עא', b)
