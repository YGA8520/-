#!/usr/bin/env python3
"""Puts new front pages (haskamot, dedication, ...) into a FINISHED booklet PDF and keeps the parity of every page that was already there.

usage: python merge_front_pages.py plan.json [--only NAME]

plan.json = a list of booklets:
  [{"name": "pilpula", "booklet": "in/chavurot.pdf", "out": "out/pilpula.pdf",
    "ops": [{"after": 4, "insert": ["out/haskamot-pilpula-silver.pdf", "dedication.pdf"]},
            {"replace": [5, 7], "with": ["out/haskamot-silver.pdf"]}]}]
  page numbers are the physical pages of the ORIGINAL booklet, 1 = the outer cover; relative paths are relative to plan.json.
  "after": N           the sections are put after original page N
  "replace": [A, B]    original pages A..B are taken out and the sections take their place
  every file in "insert" / "with" is one section (all of its pages, in order).

The rules (the booklet is Hebrew: an odd page is a left-hand page, the front of a leaf, where a title page, a divider, the haskamot and the
dedication stand; the even page is the back of the same leaf):
  * every section starts on an odd page: when it would fall on an even page an empty white page goes before it (the back of the previous leaf);
  * after the new pages, the next original page falls on a page of its own parity: when it would not, an empty page is added there,
    so every later page is shifted by an even number of pages - odd stays odd, even stays even (the script proves it page by page);
  * nothing inside the pages is changed: the vector pages are placed as they are (fitted to the page size of the booklet), a page number
    printed on a page and a table of contents with page numbers keep their values; bookmarks follow their pages.
"""
import argparse, json, os, sys
import pymupdf


def plan_sequence(n_orig, ops):
    """the final order: ('o', p) original page p, ('s', path, k) page k of a section, ('b',) an empty page"""
    after = {}
    replaced = {}
    skip = set()
    for op in ops:
        if 'after' in op:
            after.setdefault(op['after'], []).extend(op['insert'])
        else:
            a, b = op['replace']
            assert 1 <= a <= b <= n_orig
            replaced[a] = op['with']
            skip.update(range(a, b + 1))
    seq = []

    def put_sections(paths):
        for path in paths:
            if (len(seq) + 1) % 2 == 0:
                seq.append(('b', 'before ' + os.path.basename(path)))
            for k in range(pymupdf.open(path).page_count):
                seq.append(('s', path, k))

    def align(p):
        if (len(seq) + 1) % 2 != p % 2:
            seq.append(('b', 'parity'))

    for p in range(1, n_orig + 1):
        if p in replaced:
            put_sections(replaced[p])
        if p not in skip:
            align(p)
            seq.append(('o', p))
        if p in after:
            put_sections(after[p])
    return seq


def merge(booklet, out, ops):
    b = pymupdf.open(booklet)
    n = b.page_count
    toc = b.get_toc(simple=False)
    seq = plan_sequence(n, ops)
    keep = [it[1] for it in seq if it[0] == 'o']
    # 1. take out the replaced pages (from the end, so the numbers stay valid)
    for p in sorted(set(range(1, n + 1)) - set(keep), reverse=True):
        b.delete_page(p - 1)
    cur = sorted(keep)
    assert cur == keep, 'the original pages must stay in their order'
    # 2. new pages where the sequence asks for them
    srcs = {}
    for k, it in enumerate(seq):
        if it[0] == 'o':
            assert cur[k] == it[1]
            continue
        ref = b[min(k, b.page_count - 1)].rect                         # the size of the booklet's own page at this place
        pg = b.new_page(pno=k, width=ref.width, height=ref.height)
        if it[0] == 's':
            src = srcs.setdefault(it[1], pymupdf.open(it[1]))
            pg.show_pdf_page(pg.rect, src, it[2])
        cur.insert(k, None)
    assert len(cur) == len(seq) == b.page_count
    b.save(out, garbage=3, deflate=True)

    # proof
    o = pymupdf.open(out)
    pos = {it[1]: k + 1 for k, it in enumerate(seq) if it[0] == 'o'}
    bad = [p for p, q in pos.items() if p % 2 != q % 2]
    orig = pymupdf.open(booklet)
    same = all(orig[p - 1].get_text() == o[q - 1].get_text() for p, q in pos.items() if p in (1, 2, n) or p % 37 == 0)
    sec_starts = [k + 1 for k, it in enumerate(seq) if it[0] == 's' and it[2] == 0]
    new_toc = o.get_toc(simple=False)
    toc_ok = len(new_toc) == len(toc) and all(t[2] == -1 or nt[2] == pos.get(t[2], nt[2]) for t, nt in zip(toc, new_toc))
    rep = {
        'pages': [n, o.page_count], 'added': o.page_count - n,
        'sections start on pages': sec_starts, 'all start odd': all(s % 2 for s in sec_starts),
        'empty pages added at': [k + 1 for k, it in enumerate(seq) if it[0] == 'b'],
        'original pages whose parity changed': len(bad), 'sample of pages identical': same,
        'bookmarks': f'{len(toc)} ({"follow their pages" if toc_ok else "CHECK"})',
    }
    return rep, seq, bad


def front_list(seq, upto):
    out = []
    for k, it in enumerate(seq[:upto]):
        out.append(f"{k + 1}:{'orig ' + str(it[1]) if it[0] == 'o' else ('empty' if it[0] == 'b' else os.path.basename(it[1]).replace('.pdf', '') + (f' p{it[2] + 1}' if it[2] else ''))}")
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('--only', default=None)
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(a.plan))
    rel = lambda x: x if os.path.isabs(x) else os.path.join(base, x)
    fails = 0
    for bk in json.load(open(a.plan)):
        if a.only and bk['name'] != a.only:
            continue
        ops = []
        for op in bk['ops']:
            op = dict(op)
            for key in ('insert', 'with'):
                if key in op:
                    op[key] = [rel(x) for x in op[key]]
            ops.append(op)
        os.makedirs(os.path.dirname(rel(bk['out'])), exist_ok=True)
        rep, seq, bad = merge(rel(bk['booklet']), rel(bk['out']), ops)
        print(f"== {bk['name']}: {json.dumps(rep, ensure_ascii=False)}")
        print('   front:', ' | '.join(front_list(seq, 16)))
        fails += bool(bad) or not rep['all start odd']
    sys.exit(1 if fails else 0)
