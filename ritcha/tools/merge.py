"""Merge the original compilation with the units from the new files: de-duplicate, sort by siman, keep a report."""
import re, json, copy
from model import build, heb_num
import newsrc

# ------------------------------------------------------------------ text fingerprints
NIQ = re.compile('[֑-ׇ]')
def norm_words(text):
    t = NIQ.sub('', text)
    t = re.sub(r'[\'"״׳`´’“”\[\]\(\)\{\}\.,:;!?\-–—_*=/\\|]', ' ', t)
    return t.split()

def shingles(words, n=3):
    if len(words) >= n + 3: n = 3
    elif len(words) >= 3: n = 2
    else: n = 1
    return {tuple(words[i:i + n]) for i in range(max(1, len(words) - n + 1))}

def qtext(blocks): return ' '.join(''.join(t for t, _ in b['runs']) for b in blocks if b['kind'] in ('q', 'sub'))

class Item:
    def __init__(self, siman, blocks, src, section=None):
        self.siman, self.blocks, self.src, self.section = siman, blocks, src, section
        self.dups = []
        self.refresh()
    def refresh(self):
        self.words = norm_words(qtext(self.blocks)); self.sh = shingles(self.words)
        self.n = len(self.words)

def cov(a, b):          # share of a's shingles that occur in b
    return len(a.sh & b.sh) / len(a.sh) if a.sh else 0.0

def gem(s):             # numeric value of a siman written in Hebrew letters
    v = {'א':1,'ב':2,'ג':3,'ד':4,'ה':5,'ו':6,'ז':7,'ח':8,'ט':9,'י':10,'כ':20,'ך':20,'ל':30,'מ':40,'ם':40,'נ':50,'ן':50,'ס':60,'ע':70,'פ':80,'ף':80,'צ':90,'ץ':90,'ק':100,'ר':200,'ש':300,'ת':400}
    return sum(v.get(c, 0) for c in s)

# ------------------------------------------------------------------ name style used in the printed issues: [הערת ה"ר …]
def conv_name(b):
    t = ''.join(x for x, _ in b['runs']).strip()
    if t.startswith('הערת') or t.startswith('ראש הכולל') or t.startswith('בני החבורה'):
        return t
    t = re.sub(r'^האברך החשוב\s+', '', t)
    t = re.sub(r'\bהרב\b', 'ה"ר', t)
    t = re.sub(r'\s*שליט"א$', '', t) if False else t
    if t.startswith('ה"ר'): t = 'הערת ' + t
    return t

def merge():
    log = []     # (decision, new_src, new_text, old_src, old_text, a, b)
    comp = build('input_document.xml')
    # split the compilation: part 1 (simanim + שאלות שונות) / part 2 (from 'שאלה להלכה למעשה')
    cut = next(i for i, s in enumerate(comp) if s['title'] and s['title'].startswith('שאלה להלכה למעשה'))
    part1, part2 = comp[:cut], comp[cut:]
    general_title = 'שאלות שונות בעניני תפילה'

    pool = []                                    # Items, in insertion order
    def add(unit_siman, blocks, src, section=None):
        pool.append(Item(unit_siman, blocks, src, section))

    def consider(siman, blocks, src, section=None):
        N = Item(siman, blocks, src, section)
        same = [E for E in pool if (E.section or None) == (section or None) or not (E.section or section)]
        inside = [E for E in same if cov(E, N) >= 0.6]          # existing items whose text is (mostly) inside N
        if len(inside) >= 2 or (len(inside) == 1 and cov(N, inside[0]) < 0.6):
            keep = inside[0]
            names_old = [x for E in inside for x in E.blocks if x['kind'] == 'name']
            for E in inside[1:]:
                pool.remove(E)
                log.append(('אוחד לשאלה אחת (נכלל בגרסה המלאה)', src, qtext(E.blocks), keep.src, '', round(cov(E, N), 2), 0))
            keep.blocks = copy.deepcopy(N.blocks)
            if not any(x['kind'] == 'name' for x in keep.blocks): keep.blocks += names_old[:1]
            keep.src = keep.src + ' ← ' + src
            keep.refresh()
            keep.dups.append(src)
            log.append(('הוחלף בגרסה מלאה יותר', src, qtext(N.blocks), keep.src, '', 0, 1.0))
            return
        best, bs = None, 0.0
        for E in same:
            sc = max(cov(N, E), cov(E, N))
            if sc > bs: best, bs = E, sc
        if best is not None and bs >= 0.6:
            a, b = cov(N, best), cov(best, N)       # a: how much of N is in E ; b: how much of E is in N
            if a >= 0.6 and b >= 0.6:
                winner = 'N' if (N.n > 1.25 * best.n and N.n >= best.n + 8) else 'E'
            elif a >= 0.6: winner = 'E'
            else: winner = 'N'
            if winner == 'N':
                names_old = [x for x in best.blocks if x['kind'] == 'name']
                best.blocks = copy.deepcopy(N.blocks)
                if not any(x['kind'] == 'name' for x in best.blocks): best.blocks += names_old
                best.src = best.src + ' ← ' + src
                best.refresh()
                best.dups.append(src)
                log.append(('הוחלף בגרסה מלאה יותר', src, qtext(N.blocks), best.src, '', round(a, 2), round(b, 2)))
            else:
                best.dups.append(src)
                if any(x['kind'] == 'name' for x in N.blocks) and not any(x['kind'] == 'name' for x in best.blocks):
                    best.blocks += [x for x in N.blocks if x['kind'] == 'name']
                    tag = 'כפילות (נוסף שם הכותב)'
                else: tag = 'כפילות'
                log.append((tag, src, qtext(N.blocks), best.src, qtext(best.blocks), round(a, 2), round(b, 2)))
            return
        if best is not None and bs >= 0.4:
            log.append(('דומה – נשאר (לבדיקה)', src, qtext(N.blocks), best.src, qtext(best.blocks), round(cov(N, best), 2), round(cov(best, N), 2)))
        pool.append(N)

    # priority 1: the printed pair (its order is the editor's order)
    for u in newsrc.UNITS:
        if u['src'].startswith('z1 סה-סו') or u['src'].startswith('z1 סימן ח'):
            consider(u['siman'], u['blocks'], u['src'], u['section'])
    # priority 2: the compilation
    for s in part1:
        for e in s['entries']:
            if e['type'] != 'item': continue
            consider(s['num'], copy.deepcopy(e['blocks']), 'חוברת קיימת', s['title'])
    # priority 3: everything else
    for u in newsrc.UNITS:
        if u['src'].startswith('z1 סה-סו') or u['src'].startswith('z1 סימן ח'): continue
        consider(u['siman'], u['blocks'], u['src'], u['section'])


    # ---- same question in an earlier (raw) wording and in the wording of the printed issue -> keep the printed one
    SUPERSEDE = [   # (prefix of the text to drop, prefix of the text to keep)
        ('בדין שהה כדי לגמור את כולה', 'יש לחקור בדין שהייה'),
        ("בביאור הלכה ד\"ה קראה הביא דמדרך החיים משמע דאפי' שהה", 'בביאור הלכה ד"ה קראה הביא דמדרך החיים משמע דאם'),
        ('יש לדון במי שנכנס לבית הכנסת ומצא ציבור', 'יש לדון במי שנמצא בבית הכנסת בשעה'),
        ('פסק רבינו המשנה ברורה [סק"ו]', 'פסק המשנה ברורה [סימן סד'),
    ]
    for drop_p, keep_p in SUPERSEDE:
        d = next((x for x in pool if qtext(x.blocks).startswith(drop_p)), None)
        k = next((x for x in pool if qtext(x.blocks).startswith(keep_p)), None)
        if d is None or k is None: raise SystemExit('SUPERSEDE not found: ' + drop_p)
        pool.remove(d)
        k.dups.append(d.src + ' (ניסוח קודם)')
        log.append(('כפילות (אותה שאלה בניסוח קודם – נשארה הגרסה המעובדת)', k.src, qtext(k.blocks), d.src, qtext(d.blocks), 0, 0))

    # ---- assemble part 1
    by = {}
    for it in pool:
        key = it.siman if it.siman else '__' + (it.section or general_title)
        by.setdefault(key, []).append(it)
    sections = []
    for key in sorted([k for k in by if not k.startswith('__')], key=gem):
        sections.append(dict(num=key, title=None, entries=[dict(type='item', blocks=x.blocks, src=x.src, dups=x.dups) for x in by[key]]))
    for key in [k for k in by if k.startswith('__')]:
        sections.append(dict(num=None, title=key[2:], entries=[dict(type='item', blocks=x.blocks, src=x.src, dups=x.dups) for x in by[key]]))
    # rename name blocks to the printed style
    for s in sections:
        for e in s['entries']:
            for b in e['blocks']:
                if b['kind'] == 'name': b['runs'] = [(conv_name(b), {})]
    return sections, part2, log, pool

if __name__ == '__main__':
    sections, part2, log, pool = merge()
    from collections import Counter
    print('items in part 1:', sum(1 for s in sections for e in s['entries']), ' simanim:', [s['num'] or s['title'] for s in sections])
    print(Counter(l[0] for l in log))
    json.dump(log, open('merge_log.json', 'w'), ensure_ascii=False, indent=1)
    for l in log:
        if l[0].startswith('דומה'):
            print(l[0], '|', l[1], '|', l[2][:60], '||', l[3], '|', l[4][:60], l[5], l[6])
