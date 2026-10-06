#!/usr/bin/env python3
"""lines.json (from extract.py) + design/manifest.py  ->  work/units.json  (+ work/units.txt for review).

Blocks of a unit:
  h2 {runs}                     siman / big section heading
  h3 {runs}                     small bold heading
  cap {runs}                    small caption ("סעי' ג'.")
  note {runs}                   short remark ("שאלה אחת רשות!")
  q  {label, kicker, runs, more:[runs], subs:[{label,runs}], n}   question (n ruled answer lines)
  ans {head, paras:[{runs,sub}]}  answer
  p  {runs}                     plain paragraph
  rules {items:[{label,runs}]}  "כללי המבחן"
  close {text} / closenote {runs}
  lines {n}
runs: [[text, flags]] ; flags: b bold, u underline, s small
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'design'))
from manifest import UNITS, DROPPED  # noqa: E402

ROOT = os.path.join(HERE, '..')
LINES = os.path.join(ROOT, 'work', 'lines.json')

HEB = 'א-ת'
GEM = {'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9, 'י': 10, 'כ': 20, 'ל': 30, 'מ': 40,
       'נ': 50, 'ס': 60, 'ע': 70, 'פ': 80, 'צ': 90, 'ק': 100, 'ר': 200, 'ש': 300, 'ת': 400}
INV = {v: k for k, v in GEM.items()}


def gem_value(s):
    """value of a gematria label, None if it is not a plausible numeral"""
    if not s or not all(c in GEM for c in s):
        return None
    if len(s) == 1:
        return GEM[s]
    if s in ('טו', 'טז'):
        return 15 if s == 'טו' else 16
    if len(s) == 2:
        a, b = GEM[s[0]], GEM[s[1]]
        if a >= 10 and b < 10 and a > b:
            return a + b
        if a >= 100 and b >= 10 and a > b and b % 10 == 0:
            return a + b
    return None


def to_gem(n):
    s = ''
    for v in (400, 300, 200, 100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1):
        while n >= v:
            s += INV[v]
            n -= v
    return s.replace('יה', 'טו').replace('יו', 'טז')


def label_value(lab):
    if lab is None:
        return None
    if lab.isdigit():
        return int(lab)
    return gem_value(lab)


NOISE_RES = [
    re.compile(r'^בס\s*["״]?\s*ד$'),
    re.compile(r'^בסייעתא\s+דשמיא$'),
    re.compile(r'^שם\s*[:_\s]*(?:ציון\s*[:_\s]*)?$'),
    re.compile(r'^ציון\s*[:_\s]*$'),
    re.compile(r'^הרב\s*[:_\s]*$'),
    re.compile(r'^~\s*\d+\s*~$'),
    re.compile(r"^'?ברומו של עולם'?$"),
]


def is_noise(t, base):
    t = t.strip()
    if not t:
        return True
    for r in NOISE_RES:
        if r.match(t):
            return True
    if base > 775 and len(t) <= 2:      # page numbers of the source
        return True
    if re.fullmatch(r'[.,;:\-–\s]+', t):  # stray punctuation line
        return True
    return False


def line_text(l):
    return ''.join(r['t'] for r in l['runs'])


def is_rule(t):
    return bool(re.fullmatch(r'[_\s]+', t)) and t.count('_') >= 6


LABEL_RE = re.compile(r'^\s*(?:(\d{1,2})|([%s]{1,3}))\s*([.)\]\(\[:\'׳])+\s*' % HEB)
LAST_LABEL_DOT = True
LABEL_RE_NOPUNCT = re.compile(r'^\s*(\d{1,2})\s+(?=[%s])' % HEB)


def split_label(text, allow_bare_digit=False):
    m = LABEL_RE.match(text)
    if m:
        lab = m.group(1) or m.group(2)
        if m.group(2) and gem_value(lab) is None:
            return None, text
        global LAST_LABEL_DOT
        punct = re.sub(r'[%s\d\s]' % HEB, '', m.group(0))
        if set(punct) <= set("'׳"):      # "ד' הלכות" is a number inside the sentence, not a label
            return None, text
        LAST_LABEL_DOT = '.' in m.group(0)
        return lab, text[m.end():]
    if allow_bare_digit:
        m = LABEL_RE_NOPUNCT.match(text)
        if m:
            return m.group(1), text[m.end():]
    return None, text


class Row:
    def __init__(self, l, page, same_row=False):
        self.l = l
        self.page = page
        self.x0, self.x1, self.base = l['x0'], l['x1'], l['base']
        self.runs = l['runs']
        self.text = line_text(l).strip()
        self.same_row = same_row
        sizes = [r['s'] for r in self.runs if r['t'].strip()]
        self.size = max(sizes) if sizes else 12
        self.allbold = all(r['b'] for r in self.runs if r['t'].strip())


def build_items(unit, pages):
    items = []
    a, b = unit['pages']
    for pn in range(a, b + 1):
        P = pages[pn]
        ls = sorted(P['lines'], key=lambda l: (round(l['base'] / 3), -l['x1']))
        prev_base = None
        for l in ls:
            t = line_text(l).strip()
            if is_noise(t, l['base']):
                continue
            if is_rule(t):
                if items and items[-1][0] == 'rule' and items[-1][2] == pn and abs(items[-1][1] - l['base']) < 3:
                    continue
                items.append(('rule', l['base'], pn, l))
                continue
            same = prev_base is not None and abs(l['base'] - prev_base) < 3
            items.append(('row', l['base'], pn, Row(l, pn, same)))
            prev_base = l['base']
    return items


def base_size(rows):
    c = Counter()
    for r in rows:
        for run in r.runs:
            if run['t'].strip():
                c[run['s']] += len(run['t'])
    return c.most_common(1)[0][0] if c else 12


def runs_of(rows, base):
    """join rows into [[text, flags]]"""
    allbold = all(r.allbold for r in rows)
    sizes = [run['s'] for r in rows for run in r.runs if run['t'].strip()]
    all_small = bool(sizes) and max(sizes) <= base - 1.4
    out = []
    for i, r in enumerate(rows):
        for run in r.runs:
            t = run['t']
            if not t:
                continue
            f = ''
            if run['b'] and not allbold:
                f += 'b'
            if run['u']:
                f += 'u'
            if run['s'] <= base - 1.4 and not all_small:
                f += 's'
            if out and out[-1][1] == f:
                out[-1][0] += t
            else:
                out.append([t, f])
        if i < len(rows) - 1 and out and not out[-1][0].endswith(' '):
            out[-1][0] += ' '
    res = [[re.sub(r'\s+', ' ', t), f] for t, f in out]
    if res:
        res[0][0] = res[0][0].lstrip()
        res[-1][0] = res[-1][0].rstrip()
    return [r for r in res if r[0]]


def plain(runs):
    return ''.join(t for t, f in runs)


def strip_label(runs, bare=False):
    text = plain(runs)
    lab, rest = split_label(text, bare)
    if lab is None:
        return None, runs
    cut = len(text) - len(rest)
    out, pos = [], 0
    for t, f in runs:
        end = pos + len(t)
        if end <= cut:
            pos = end
            continue
        if pos < cut:
            t = t[cut - pos:]
        out.append([t, f])
        pos = end
    if out:
        out[0][0] = out[0][0].lstrip()
    return lab, out


class Para:
    def __init__(self, rows):
        self.rows = rows

    @property
    def text(self):
        return ' '.join(r.text for r in self.rows)


CLOSE_RE = re.compile(r'^(?:ב ?ה ?צ ?ל ?ח ?ה|הצלחה רבה|בהצלחה)')


def parse_unit(unit, pages):
    if unit.get('manual'):
        return manual_blocks(unit['manual'])
    items = build_items(unit, pages)
    skip = unit.get('skip_head', 0)
    kept = []
    for it in items:
        if skip and it[0] == 'row':
            skip -= 1
            continue
        kept.append(it)
    items = kept
    rows_only = [it[3] for it in items if it[0] == 'row']
    if not rows_only:
        return []
    base = base_size(rows_only)
    # geometry
    x0c = Counter(round(r.x0) for r in rows_only)
    mode_x0, mode_n = x0c.most_common(1)[0]
    justified = mode_n / len(rows_only) >= 0.30
    left = mode_x0 if justified else sorted(r.x0 for r in rows_only)[len(rows_only) // 8]
    right = sorted(r.x1 for r in rows_only)[len(rows_only) * 7 // 8]
    width = right - left
    gaps = []
    lr = None
    for it in items:
        if it[0] == 'row':
            r = it[3]
            if lr is not None and r.page == lr.page and not r.same_row:
                gaps.append(r.base - lr.base)
            lr = r
    cand = [g for g in gaps if g >= 0.9 * base]
    pitch = min(cand) if cand else 1.2 * base
    pitch = min(pitch, 1.35 * base) if min(gaps or [pitch]) > 1.35 * base else pitch

    def label_like(r):
        return split_label(r.text, True)[0] is not None

    def para_first_label(rows):
        lab = split_label(rows[0].text, True)[0]
        return lab

    def starts_new(prev, r, cur_rows=None):
        if prev is None:
            return True
        if cur_rows is not None and label_like(r):
            a = label_value(para_first_label(cur_rows))
            b = label_value(split_label(r.text, True)[0])
            if a is not None and b is not None and b == a + 1:
                return True
        if re.match(r'^\s*ה?תשובה', r.text):
            return True
        if abs(r.size - prev.size) >= 2.5:
            return True
        if r.same_row:
            return unit.get('bold_answers', False) or r.allbold != prev.allbold
        if r.page != prev.page:
            full = prev.x0 <= left + 6 and justified
            return (not full) or label_like(r) or (r.allbold and len(r.text) < 60)
        gap = r.base - prev.base
        if gap > pitch * 1.4:
            return True
        if label_like(r) and (prev.text[-1:] in '?.:)]!' or (justified and prev.x0 > left + 0.1 * width) or gap > pitch * 1.15):
            return True
        if justified and prev.x0 > left + 0.12 * width:
            return True
        if r.allbold != prev.allbold:
            return True
        return False

    seq = []
    prev = None
    for it in items:
        if it[0] == 'rule':
            if seq and seq[-1][0] == 'rules':
                seq[-1][1] += 1
            else:
                seq.append(['rules', 1])
            prev = None
            continue
        r = it[3]
        if seq and seq[-1][0] == 'para' and prev is not None and not starts_new(prev, r, seq[-1][1]):
            seq[-1][1].append(r)
        else:
            seq.append(['para', [r]])
        prev = r

    # ---------------- classification state machine ----------------
    kind = unit['kind']
    blocks = []
    st = dict(main=None, sub=None, ans=None, after_head=False, mode=None, closed=False, restart=True)
    bold_answers = unit.get('bold_answers')

    def expected_main(lab):
        v = label_value(lab)
        if v is None:
            return False
        if st['main'] is None:
            return v == 1
        if v == 1 and (not blocks or blocks[-1]['t'] in ('h2', 'h3', 'cap', 'note', 'close', 'closenote')):
            return True
        pv = label_value(st['main'])
        if pv is None:
            return False
        if lab.isdigit() != st['main'].isdigit():
            return False
        return v == pv + 1

    def expected_sub(lab):
        v = label_value(lab)
        if v is None:
            return False
        if st['sub'] is None:
            return v == 1
        pv = label_value(st['sub'])
        return pv is not None and v == pv + 1 and lab.isdigit() == st['sub'].isdigit()

    def last_q():
        for b in reversed(blocks):
            if b['t'] == 'q':
                return b
            if b['t'] in ('h2', 'h3', 'ans', 'close', 'rules'):
                return None
        return None

    for kind_, val in seq:
        if kind_ == 'rules':
            q = blocks[-1] if blocks and blocks[-1]['t'] == 'q' else None
            if q is not None and q.get('n') is None:
                q['n'] = val
            else:
                blocks.append(dict(t='lines', n=val))
            continue
        rows = val
        runs = runs_of(rows, base)
        pt = plain(runs).strip()
        big = max(r.size for r in rows)
        allb = all(r.allbold for r in rows)
        single = len(rows) <= 2
        cx = (min(r.x0 for r in rows) + max(r.x1 for r in rows)) / 2
        centered = abs(cx - pages_center(unit, pages)) < 9 and (max(r.x1 for r in rows) - min(r.x0 for r in rows)) < 0.62 * 595 and len(rows) == 1
        lab, lrest = strip_label(runs, bare=True)
        nrm = re.sub(r'[\s"\'״׳:.]+', '', pt)

        # closing wish
        if CLOSE_RE.match(pt.replace(' ', '')) and len(pt) < 30:
            blocks.append(dict(t='close', text=re.sub(r'\s+', '', pt) if re.fullmatch(r'[ב-ת !.\s]+', pt) and ' ' in pt[:4] else pt))
            st['closed'] = True
            continue
        if st['closed']:
            blocks.append(dict(t='closenote', runs=runs))
            continue
        if pt.startswith('כללי המבחן'):
            blocks.append(dict(t='h3', runs=runs))
            st['mode'] = 'rules'
            continue
        if st['mode'] == 'rules':
            if lab is not None:
                blocks.append(dict(t='rule', label=lab, runs=lrest))
                continue
            st['mode'] = None

        # size / centre based headings
        is_siman = bool(re.match(r"^(סימן|סי')\s", pt)) and len(pt) < 40
        if single and not lab and (big >= base + 2.5 or (is_siman and (centered or allb or big > base))) and len(pt) < 70 and not pt.endswith('?'):
            blocks.append(dict(t='h2', runs=runs))
            st.update(ans=None, restart=True, after_head=False)
            continue
        if st['ans'] is not None and abs(big - base) >= 2 and not re.match(r'^ה?תשובה', nrm):
            st['ans'] = None
        # answers
        if re.match(r'^ה?תשובה', nrm) and len(pt) < 45 and not lab:
            # a lone "תשובה:" heading: the paragraph before it was the (unlabelled) question
            if unit.get('qa_unlabelled') and blocks and blocks[-1]['t'] == 'p':
                blocks[-1]['t'] = 'q'
                blocks[-1].update(label=None, kicker=None, more=[], subs=[], n=None)
            a = dict(t='ans', head=runs, paras=[])
            blocks.append(a)
            st.update(ans=a, after_head=True)
            continue
        if re.match(r'^ה?תשובה', nrm):
            head, rest = split_answer_head(runs)
            a = dict(t='ans', head=head, paras=[dict(runs=rest, sub=False)] if rest else [])
            blocks.append(a)
            st.update(ans=a, after_head=False)
            continue
        # question labels
        if lab is not None and not st['after_head']:
            ok_main = expected_main(lab)
            if ok_main and st['ans'] is None and last_q() is not None and expected_sub(lab) and not LAST_LABEL_DOT:
                ok_main = False
            if st['ans'] is not None and kind in ('key', 'sheet'):
                ok_main = expected_main(lab) and not lab.isdigit() if st['main'] and not st['main'].isdigit() else expected_main(lab)
            if ok_main and not (lab.isdigit() and st['ans'] is not None and kind == 'key' and unit.get('digits_are_answers')):
                st.update(main=lab, sub=None, restart=False, ans=None, after_head=False)
                blocks.append(dict(t='q', label=lab, kicker=None, runs=lrest, more=[], subs=[], n=None))
                continue
            if st['ans'] is None and expected_sub(lab) and last_q() is not None:
                st['sub'] = lab
                last_q()['subs'].append(dict(label=lab, runs=lrest))
                continue
        # optional questions without a label
        if (st['ans'] is None or kind in ('exam', 'chavura')) and (re.match(r'^שאלה:\s', pt) or re.match(r'^שאלת רשות', pt)):
            kick = 'שאלת רשות' if pt.startswith('שאלת רשות') else 'שאלה'
            body = re.sub(r'^(שאלת רשות|שאלה)\s*:?\s*', '', pt, count=1)
            q = dict(t='q', label=None, kicker=kick, runs=strip_kicker(runs), more=[], subs=[], n=None)
            blocks.append(q)
            st.update(ans=None, sub=None)
            continue
        if single and pt.strip() == 'תורה דיליה':
            blocks.append(dict(t='h3', runs=runs))
            st['ans'] = None
            continue
        # a small centred last line of a question (wrapped) belongs to the question
        if single and not lab and st['ans'] is None and blocks and blocks[-1]['t'] == 'q' and blocks[-1].get('n') is None \
                and big <= base - 1.4 and not pt.endswith(':') and kind in ('exam', 'chavura'):
            blocks[-1]['runs'] = blocks[-1]['runs'] + [[' ', '']] + runs
            continue
        # short headings / captions
        if single and len(pt) <= 24 and re.match(r"^(סעי|סימן|סי')", pt) and kind in ('key', 'sheet'):
            blocks.append(dict(t='cap', runs=runs))
            st['ans'] = None
            continue
        if single and not lab and ((allb and len(pt) < 90 and not pt.endswith('?')) or (centered and len(pt) < 60) or
                                   (len(pt) < 60 and pt.endswith(':')) or (len(pt) < 40 and 'רשות' in pt)):
            if 'שאלה אחת רשות' in pt or 'שתי שאלות רשות' in pt or 'שאלות רשות' in pt and len(pt) < 24:
                blocks.append(dict(t='note', runs=runs))
            elif st['ans'] is not None and kind in ('key', 'sheet') and not pt.endswith(':'):
                st['ans']['paras'].append(dict(runs=runs, sub=True))
            else:
                blocks.append(dict(t='h3', runs=runs))
            if st['ans'] is None:
                pass
            continue
        # bold answers (key with bold_answers): all-bold paragraphs are answers
        bold_chars = sum(len(t) for t, f in runs if 'b' in f)
        bold_ratio = 1.0 if allb else bold_chars / max(1, len(pt))
        if bold_answers and bold_ratio >= 0.6 and not lab:
            if st['ans'] is None:
                a = dict(t='ans', head=None, paras=[])
                blocks.append(a)
                st['ans'] = a
            st['ans']['paras'].append(dict(runs=runs, sub=False))
            st['after_head'] = False
            continue
        if st['ans'] is not None:
            st['ans']['paras'].append(dict(runs=runs, sub=False))
            st['after_head'] = False
            continue
        q = last_q()
        if q is not None and blocks[-1] is q and q.get('n') is None and kind in ('exam', 'chavura', 'key'):
            q['more'].append(runs)
            continue
        if q is not None and kind in ('exam', 'chavura') and q['subs'] and blocks[-1] is q:
            q['subs'][-1]['runs'] += [[' ', '']] + runs
            continue
        blocks.append(dict(t='p', runs=runs))
    return blocks


def split_answer_head(runs):
    """'**תשובה:** text' -> (head runs, rest runs)"""
    text = plain(runs)
    m = re.match(r'^\s*(ה?תשובה[^:]{0,40}:)\s*', text)
    if not m:
        return None, runs
    cut = m.end()
    head, rest, pos = [[m.group(1), 'b']], [], 0
    for t, f in runs:
        end = pos + len(t)
        if end <= cut:
            pos = end
            continue
        if pos < cut:
            t = t[cut - pos:]
        rest.append([t, f])
        pos = end
    return head, rest


def manual_blocks(name):
    from manual import BLOCKS
    return BLOCKS[name]


def strip_kicker(runs):
    text = plain(runs)
    m = re.match(r'^\s*(שאלת רשות|שאלה)\s*:?\s*', text)
    if not m:
        return runs
    cut = m.end()
    out, pos = [], 0
    for t, f in runs:
        end = pos + len(t)
        if end <= cut:
            pos = end
            continue
        if pos < cut:
            t = t[cut - pos:]
        out.append([t, f.replace('b', '') if False else f])
        pos = end
    return out


_PC = {}


def pages_center(unit, pages):
    return 297.6


def dump(units_out):
    lines = []
    for u in units_out:
        lines.append(f"\n######## {u['id']}  pages {u['pages']}  [{u['kind']}]  {u['kicker']} | {u['title']} | {u.get('sub')}")
        for b in u['blocks']:
            t = b['t']
            if t == 'lines':
                lines.append(f"   ~~ lines x{b['n']}")
            elif t == 'close':
                lines.append(f"   == CLOSE: {b['text']}")
            elif t == 'rule':
                lines.append(f"   rule[{b['label']}] {plain(b['runs'])[:100]}")
            elif t == 'q':
                n = f" ~{b['n']}" if b.get('n') else ''
                k = f"<{b['kicker']}>" if b.get('kicker') else ''
                lines.append(f"   Q[{b['label']}]{k}{n} {fmt(b['runs'])[:140]}")
                for m in b['more']:
                    lines.append(f"        + {fmt(m)[:120]}")
                for s in b['subs']:
                    lines.append(f"        - [{s['label']}] {fmt(s['runs'])[:110]}")
            elif t == 'ans':
                h = fmt(b['head'])[:40] if b['head'] else ''
                lines.append(f"   ANS {h}  ({len(b['paras'])} paras)")
                for p_ in b['paras'][:2]:
                    lines.append(f"        . {fmt(p_['runs'])[:120]}")
            else:
                lines.append(f"   {t.upper():5s} {fmt(b['runs'])[:150]}")
    return '\n'.join(lines)


def fmt(runs):
    s = ''
    for t, f in runs:
        if 'b' in f:
            s += '**' + t + '**'
        elif 's' in f:
            s += '{' + t + '}'
        else:
            s += t
    return s


def main():
    P = {p['n']: p for p in json.load(open(LINES, encoding='utf8'))}
    covered = {}
    for u in UNITS:
        for n in range(u['pages'][0], u['pages'][1] + 1):
            covered.setdefault(n, []).append(u['id'])
    for (a, b), why in DROPPED:
        for n in range(a, b + 1):
            covered.setdefault(n, []).append('dropped')
    miss = [n for n in range(1, 103) if n not in covered]
    dup = {n: v for n, v in covered.items() if len(v) > 1}
    print('pages not covered:', miss, ' pages covered twice:', dup)
    out = []
    for u in UNITS:
        uu = dict(u)
        uu['blocks'] = parse_unit(u, P)
        out.append(uu)
    json.dump(out, open(os.path.join(ROOT, 'work', 'units.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    open(os.path.join(ROOT, 'work', 'units.txt'), 'w', encoding='utf8').write(dump(out))
    print('units', len(out), 'blocks', sum(len(u['blocks']) for u in out))


if __name__ == '__main__':
    main()
