#!/usr/bin/env python3
"""docx -> content-model JSON used by the typesetting engine.

Content model
  meta       : free-form dict (filled by manifest / heuristics)
  blocks     : list of {t:'h2'|'h3'|'p', runs:[{t, b?, sm?, fn?}]}
  footnotes  : {id: [runs]}
Run flags: b = bold, sm = source/citation in brackets (set smaller), fn = footnote id.
"""
import re, sys, json
import docx
from docx.oxml.ns import qn
from lxml import etree

HEB = 'א-ת'
GERESH, GERSHAYIM = '׳', '״'


# ---------------------------------------------------------------- text cleaning
def _fix_quotes_len(s):
    """ASCII / typographic quotes -> geresh (׳) and gershayim (״). No ASCII quote is left in the output."""
    s = s.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'").replace('\u05f4', '"').replace('\u05f3', "'")
    s = re.sub(r'(?<=[%s\u05f4"])F(?![A-Za-z])' % HEB, '\u05db', s)         # a Latin F typed on a Hebrew keyboard = כ
    s = re.sub(r'(?<=[%s])"(?=[%s])' % (HEB, HEB), GERSHAYIM, s)           # ש"ס  -> ש״ס
    s = re.sub(r'(?<=[%s\.\)\]:,])"(?=[\s\.,;:\)\]]|$)' % HEB, GERSHAYIM, s)  # closing quote
    s = re.sub(r'(?:(?<=^)|(?<=[\s\(\[]))"(?=[%s])' % HEB, GERSHAYIM, s)       # opening quote
    s = re.sub(r"(?<=[%s])'" % HEB, GERESH, s)                                # ה' -> ה׳
    s = re.sub(r"(?:(?<=^)|(?<=[\s\(\[]))'(?=[%s])" % HEB, GERESH, s)         # 'פתיחה
    return s.replace('"', GERSHAYIM).replace("'", GERESH)                      # whatever is left


def fix_quotes(s):
    return _fix_quotes_len(s.replace("''", '"'))                            # two apostrophes typed as one double quote (ק''ש)


def clean_ws(s):
    s = s.replace(' ', ' ').replace('\t', ' ').replace('‏', '').replace('‎', '')
    return re.sub(r' {2,}', ' ', s)


# ---------------------------------------------------------------- docx reading
def _flag(rpr, tag):
    if rpr is None:
        return False
    e = rpr.find(qn(tag))
    return e is not None and e.get(qn('w:val')) not in ('0', 'false', 'off')


def read_runs(p_el):
    out = []
    for r in p_el.iter(qn('w:r')):
        rpr = r.find(qn('w:rPr'))
        va = rpr.find(qn('w:vertAlign')) if rpr is not None else None
        sup = va is not None and va.get(qn('w:val')) == 'superscript'
        b = _flag(rpr, 'w:b') or _flag(rpr, 'w:bCs')
        fr = r.find(qn('w:footnoteReference'))
        if fr is not None:
            out.append({'t': '', 'fn': fr.get(qn('w:id'))})
            continue
        t = ''
        for x in r:
            if x.tag == qn('w:t'):
                t += x.text or ''
            elif x.tag == qn('w:tab'):
                t += ' '
            elif x.tag == qn('w:br'):
                t += ' '
        if t:
            out.append({'t': t, 'b': b, 'sup': sup})
    return out


def normalize_runs(runs):
    """merge fragments, give blank segments the style of their neighbours, clean quotes."""
    # blank segments inherit bold from neighbours when both agree
    for i, r in enumerate(runs):
        if 'fn' in r or r['t'].strip():
            continue
        prev = next((runs[j] for j in range(i - 1, -1, -1) if 'fn' in runs[j] or runs[j]['t'].strip()), None)
        nxt = next((runs[j] for j in range(i + 1, len(runs)) if 'fn' in runs[j] or runs[j]['t'].strip()), None)
        if prev and nxt and 'fn' not in prev and 'fn' not in nxt and prev['b'] == nxt['b']:
            r['b'] = prev['b']
            if prev.get('sm') == nxt.get('sm'):
                r['sm'] = prev.get('sm')
    merged = []
    for r in runs:
        r = dict(r)
        if 'fn' not in r:
            r['t'] = clean_ws(r['t'])
        if merged and 'fn' not in r and 'fn' not in merged[-1] and merged[-1].get('b') == r.get('b') and merged[-1].get('sm') == r.get('sm'):
            merged[-1]['t'] += r['t']
        else:
            merged.append(r)
    # collapse double spaces across run borders, trim paragraph ends, fix quotes over full text
    full = ''.join(r['t'] for r in merged if 'fn' not in r)
    fixed_full = fix_quotes(re.sub(r' {2,}', ' ', full))
    # re-distribute fixed text back over runs (fix_quotes is length preserving; space collapsing is not) -> do per-run instead
    for r in merged:
        if 'fn' not in r:
            r['t'] = r['t']
    # fix quotes using run-spanning context: apply on text with sentinel chars for fn markers
    text = ''
    spans = []
    for r in merged:
        if 'fn' in r:
            text += ''
            spans.append(None)
        else:
            spans.append((len(text), len(text) + len(r['t'])))
            text += r['t']
    text = re.sub(r' {2,}', lambda m: ' ', text) if False else text
    fixed = _fix_quotes_len(text)
    assert len(fixed) == len(text)
    for r, sp in zip(merged, spans):
        if sp:
            r['t'] = fixed[sp[0]:sp[1]]
    # collapse repeated spaces that straddle runs
    for i in range(1, len(merged)):
        a, b = merged[i - 1], merged[i]
        if 'fn' not in a and 'fn' not in b and a['t'].endswith(' ') and b['t'].startswith(' '):
            b['t'] = b['t'].lstrip(' ')
    # trim
    while merged and 'fn' not in merged[0] and not merged[0]['t'].strip():
        merged.pop(0)
    while merged and 'fn' not in merged[-1] and not merged[-1]['t'].strip():
        merged.pop()
    if merged and 'fn' not in merged[0]:
        merged[0]['t'] = merged[0]['t'].lstrip()
    if merged and 'fn' not in merged[-1]:
        merged[-1]['t'] = merged[-1]['t'].rstrip()
    merged = [r for r in merged if 'fn' in r or r['t']]
    # re-merge after trimming
    out = []
    for r in merged:
        if out and 'fn' not in r and 'fn' not in out[-1] and out[-1].get('b') == r.get('b') and out[-1].get('sup') == r.get('sup') and out[-1].get('sm') == r.get('sm'):
            out[-1]['t'] += r['t']
        else:
            out.append(r)
    for r in out:
        r.pop('sup', None)
    return out


# ---------------------------------------------------------------- small "source" brackets
BR = re.compile(r'\[[^\[\]]{2,110}\]|\([^()]{2,90}\)')


def mark_sources(runs, max_words=14, heuristic=True):
    """flag short bracketed spans ([...] or (...)) as `sm` (citations set in a smaller size)."""
    text = ''
    bold = []
    for r in runs:
        if 'fn' in r:
            text += ''
            bold.append(False)
        else:
            text += r['t']
            bold.extend([r.get('b', False)] * len(r['t']))
    small = [False] * len(text)
    for m in (BR.finditer(text) if heuristic else []):
        inner = m.group(0)
        if '' in inner:
            continue
        words = inner.split()
        if len(words) > max_words or not re.search('[%s]' % HEB, inner):
            continue
        if re.search(r'וז[״"]ל|וז״ל', inner):
            continue
        for i in range(m.start(), m.end()):
            small[i] = True
    out = []
    pos = 0
    for r in runs:
        if 'fn' in r:
            out.append(r)
            pos += 1
            continue
        s = r['t']
        i = 0
        while i < len(s):
            j = i
            while j < len(s) and small[pos + j] == small[pos + i]:
                j += 1
            seg = {'t': s[i:j]}
            if r.get('b'):
                seg['b'] = True
            if small[pos + i]:
                seg['sm'] = True
            out.append(seg)
            i = j
        pos += len(s)
    return out


# ---------------------------------------------------------------- paragraph classification
SECTION = re.compile(r'^(חלק|פרק|חלק)\s+([א-ת][\'׳"״]?[א-ת]?)\s*[:.\-–]?\s*(.*)$')


SPACE_BEFORE_PUNCT = re.compile(r'[ \t\u00a0]+(?=[,.;:](?!\.))')   # " ," / " ." (an ellipsis " ..." is left alone)


def fix_space_before_punct(runs):
    """remove a space typed in front of , . ; : (also when the space and the sign sit in different runs); runs are changed in place"""
    prev = None
    for r in runs:
        if 'fn' in r or not r.get('t'):
            continue
        r['t'] = SPACE_BEFORE_PUNCT.sub('', r['t'])
        if prev is not None and r['t'][0] in ',.;:' and r['t'][:2] != '..' and prev['t'][-1:] in ' \t\u00a0':
            prev['t'] = prev['t'].rstrip(' \t\u00a0')
        prev = r
    return runs


def runs_text(runs):
    return ''.join(r['t'] for r in runs if 'fn' not in r)


def all_bold(runs):
    t = [r for r in runs if 'fn' not in r and re.search(r'[\w\u05d0-\u05ea]', r['t'])]
    return bool(t) and all(r.get('b') for r in t)


def as_heading_runs(runs):
    """all text bold, footnote refs kept, one trailing period removed."""
    out = []
    for r in runs:
        if 'fn' in r:
            out.append(r)
        else:
            out.append({'t': r['t'], 'b': True})
    for r in reversed(out):
        if 'fn' not in r and r['t'].strip():
            r['t'] = re.sub(r'\s*\.\s*$', '', r['t'])
            break
    return out


def parse_docx(path):
    d = docx.Document(path)
    fns = {}
    for rel in d.part.rels.values():
        if rel.reltype.endswith('/footnotes'):
            root = etree.fromstring(rel.target_part.blob)
            for fn in root.findall(qn('w:footnote')):
                fid = fn.get(qn('w:id'))
                if fid in ('-1', '0'):
                    continue
                parts = []
                for p in fn.iter(qn('w:p')):
                    rr = [r for r in read_runs(p) if 'fn' not in r]
                    rr = normalize_runs(rr)
                    if rr:
                        parts.append(rr)
                # footnote may contain several paragraphs -> join with space
                runs = []
                for k, pr in enumerate(parts):
                    if k:
                        runs.append({'t': ' '})
                    runs.extend(pr)
                runs = normalize_runs(runs)
                # footnote text is plain: drop bold except explicit
                runs = mark_sources(runs)
                if runs:
                    fns[fid] = runs
    paras = []
    for p in d.paragraphs:
        runs = normalize_runs(read_runs(p._p))
        if not runs or (not runs_text(runs).strip() and not any('fn' in r for r in runs)):
            continue
        align = {0: 'right', 1: 'center', 2: 'left', 3: 'justify', None: None}.get(p.alignment.real if p.alignment is not None else None)
        paras.append({'style': p.style.name, 'align': align, 'runs': runs})
    return paras, fns


def classify(paras):
    """turn raw paragraphs into blocks (h2 / h3 / p). Top-matter paragraphs are returned separately in `head`."""
    blocks, head = [], []
    body_started = False
    for p in paras:
        runs, text = p['runs'], runs_text(p['runs']).strip()
        n = len(text)
        if not body_started:
            looks_head = (n <= 60 and not any('fn' in r for r in runs)) or text.startswith('בס"ד') or text.startswith('בס״ד')
            is_heading_style = p['style'].lower().startswith('heading') or p['style'].startswith('כותרת')
            if looks_head and not (all_bold(runs) and p['align'] == 'center' and not is_heading_style and head):
                head.append({'text': text, 'style': p['style'], 'align': p['align'], 'bold': all_bold(runs)})
                continue
            if is_heading_style and n <= 140:
                head.append({'text': text, 'style': p['style'], 'align': p['align'], 'bold': all_bold(runs)})
                continue
            body_started = True
        if all_bold(runs) and (p['align'] == 'center' or n <= 140):
            m = SECTION.match(text.replace('׳', "'"))
            if m and not any('fn' in r for r in runs):
                blocks.append({'t': 'h2', 'runs': [{'t': ('%s %s' % (m.group(1), m.group(2))).replace("'", '׳').strip()}]})
                rest = m.group(3).strip()
                if rest:
                    blocks.append({'t': 'h3', 'runs': [{'t': rest.rstrip('.'), 'b': True}]})
            else:
                blocks.append({'t': 'h3', 'runs': as_heading_runs(runs)})
            continue
        if all_bold(runs):   # long all-bold paragraph: sub-heading-ish
            blocks.append({'t': 'h3', 'runs': as_heading_runs(runs)})
            continue
        blocks.append({'t': 'p', 'runs': mark_sources(runs)})
    return blocks, head


if __name__ == '__main__':
    paras, fns = parse_docx(sys.argv[1])
    blocks, head = classify(paras)
    print(json.dumps({'head': head, 'blocks': blocks[:int(sys.argv[2]) if len(sys.argv) > 2 else 8], 'nfoot': len(fns)}, ensure_ascii=False, indent=1)[:4000])
