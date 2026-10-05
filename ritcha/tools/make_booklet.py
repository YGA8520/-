"""Whole pipeline: compilation + new files -> merged, de-duplicated booklet (docx)."""
import sys, json, copy
import merge, build_docx
from merge import heb_num

OUT = sys.argv[1] if len(sys.argv) > 1 else 'booklet.docx'

def prepare_part2(part2):
    out = []
    for s in part2:
        if s['title'] == 'שאלות לעיונא':          # this title is not used any more
            continue
        s = copy.deepcopy(s)
        if s['title'] and s['title'].startswith('שאלה להלכה למעשה'):
            s['title'] = 'שאלה להלכה למעשה'        # without ' – בין הזמנים'
        s['entries'] = [e for e in s['entries'] if e['type'] == 'item']
        for e in s['entries']:
            for b in e['blocks']:
                if b['kind'] == 'q':
                    b['runs'] = build_docx.drop_prefix(b['runs'])
        out.append(s)
    return out

if __name__ == '__main__':
    part1, part2, log, pool = merge.merge()
    part2 = prepare_part2(part2)
    build_docx.package(part1, part2, OUT)
    n1 = sum(1 for s in part1 for e in s['entries'] if e['type'] == 'item')
    n2 = sum(1 for s in part2 for e in s['entries'] if e['type'] == 'item')
    print('wrote', OUT, '| part 1:', len(part1), 'sections', n1, 'questions | part 2:', len(part2), 'sections', n2, 'questions')
    json.dump(dict(part1=part1, part2=part2), open('booklet_model.json', 'w'), ensure_ascii=False)
