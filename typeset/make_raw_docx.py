#!/usr/bin/env python3
"""A raw-text Word file of the articles of one author (or of the whole booklet), for a proofreader.

usage: python make_raw_docx.py book.doc.json out.docx ["author fragment"]

What is kept: the text, the paragraphs, the names of the styles that the text carries (title, author, subtitle, part heading, sub-heading, body, bold, small source,
footnote ...), real Word footnotes, tables.  What is left out: every definition of those styles (no font, no size, no spacing, no alignment, no columns), the typesetting
(frames, ornaments, running heads, page numbers, covers, table of contents), every picture and the document properties - the file has no design in it and no metadata."""
import json, re, sys, zipfile
from xml.sax.saxutils import escape as _esc

NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
NAME = {  # style id -> Hebrew display name (the same names as in the booklet's Word file)
    'Body': 'גוף הטקסט', 'ArticleTitle': 'כותרת מאמר', 'ArticlePart': 'כותרת חלק', 'SubHeading': 'כותרת משנה', 'ArticleAuthor': 'שם המחבר',
    'ArticleSubtitle': 'תת כותרת מאמר', 'TableText': 'טקסט טבלה', 'SmallSource': 'מקור קטן', 'BodyBold': 'הדגשה בגוף', 'FootSmall': 'מקור קטן בהערה', 'FootNum': 'מספר הערה בתחתית הערה',
}
_CTRL = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f]')


def esc(t):
    return _esc(_CTRL.sub('', t))


def run(text, rstyle=None, bold=False):
    if not text:
        return ''
    pr = (f'<w:rStyle w:val="{rstyle}"/>' if rstyle else '') + ('<w:b/><w:bCs/>' if bold else '')
    return f'<w:r>{"<w:rPr>" + pr + "</w:rPr>" if pr else ""}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def para(content, style):
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/><w:bidi/></w:pPr>{content}</w:p>'


class Notes:
    def __init__(self):
        self.items = []

    def ref(self, runs):
        n = len(self.items) + 1
        body = ''.join(run(r['t'], 'FootSmall' if r.get('sm') else None) for r in runs if 'fn' not in r)
        self.items.append(f'<w:footnote w:id="{n}"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/><w:bidi/></w:pPr><w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>'
                          f'<w:r><w:t xml:space="preserve"> </w:t></w:r>{body}</w:p></w:footnote>')
        return f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteReference w:id="{n}"/></w:r>'


def runs_xml(notes, art, runs):
    out = ''
    for r in runs:
        if 'fn' in r:
            src = art['footnotes'].get(r['fn'])
            if src:
                out += notes.ref(src)
        elif r.get('sm'):
            out += run(r['t'], 'SmallSource', bold=bool(r.get('b')))
        elif r.get('b'):
            out += run(r['t'], 'BodyBold')
        else:
            out += run(r['t'])
    return out


def table_xml(art, b):
    rows = ''
    for row in b['rows']:
        cells = ''
        for cell in row:
            txt = ''.join(run(r['t'], bold=bool(r.get('b'))) for r in cell if 'fn' not in r)
            cells += f'<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>{para(txt, "TableText")}</w:tc>'
        rows += f'<w:tr>{cells}</w:tr>'
    bd = ''.join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="auto"/>' for s in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'))
    return f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:bidiVisual/><w:tblBorders>{bd}</w:tblBorders></w:tblPr><w:tblGrid/>{rows}</w:tbl>'


def styles_xml():
    def pst(sid, name, outline=None, nxt=None):
        return (f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/><w:basedOn w:val="Normal"/>' + (f'<w:next w:val="{nxt}"/>' if nxt else '') +
                '<w:qFormat/>' + (f'<w:pPr><w:outlineLvl w:val="{outline}"/></w:pPr>' if outline is not None else '') + '</w:style>')

    def cst(sid, name, rpr=''):
        return f'<w:style w:type="character" w:styleId="{sid}"><w:name w:val="{name}"/><w:basedOn w:val="DefaultParagraphFont"/><w:qFormat/>' + (f'<w:rPr>{rpr}</w:rPr>' if rpr else '') + '</w:style>'
    s = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {NS}>'
    s += '<w:docDefaults><w:rPrDefault><w:rPr><w:lang w:val="he-IL" w:eastAsia="he-IL" w:bidi="he-IL"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:bidi/></w:pPr></w:pPrDefault></w:docDefaults>'
    s += '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
    s += '<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/></w:style>'
    s += pst('Body', NAME['Body'])
    s += pst('ArticleTitle', NAME['ArticleTitle'], outline=0, nxt='Body')       # only the structure (navigation pane): no look
    s += pst('ArticlePart', NAME['ArticlePart'], outline=1, nxt='Body')
    s += pst('SubHeading', NAME['SubHeading'], outline=2, nxt='Body')
    s += pst('ArticleAuthor', NAME['ArticleAuthor'])
    s += pst('ArticleSubtitle', NAME['ArticleSubtitle'])
    s += pst('TableText', NAME['TableText'])
    s += '<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/><w:qFormat/></w:style>'
    s += cst('SmallSource', NAME['SmallSource'])
    s += cst('BodyBold', NAME['BodyBold'], '<w:b/><w:bCs/>')
    s += cst('FootSmall', NAME['FootSmall'])
    s += cst('FootNum', NAME['FootNum'])
    s += '<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/><w:basedOn w:val="DefaultParagraphFont"/><w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>'
    return s + '</w:styles>'


def build(doc_json, out, author=None):
    data = json.load(open(doc_json, encoding='utf8'))
    arts = [a for a in data['articles'] if not author or author in (a.get('author') or '')]
    notes, body = Notes(), ''
    for art in arts:
        body += para(run(art['title']), 'ArticleTitle')
        if art.get('subtitle'):
            body += para(run(art['subtitle']), 'ArticleSubtitle')
        if art.get('author'):
            body += para(run(art['author']), 'ArticleAuthor')
        for b in art['blocks']:
            if b['t'] == 'p':
                body += para(runs_xml(notes, art, b['runs']), 'Body')
            elif b['t'] == 'h2':
                body += para(runs_xml(notes, art, b['runs']), 'ArticlePart')
            elif b['t'] == 'h3':
                body += para(runs_xml(notes, art, b['runs']), 'SubHeading')
            elif b['t'] == 'tbl':
                body += table_xml(art, b) + '<w:p/>'
    sect = '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/><w:bidi/></w:sectPr>'
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{body}{sect}</w:body></w:document>'
    footnotes = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes {NS}>'
                 '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
                 '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>' + ''.join(notes.items) + '</w:footnotes>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {NS}><w:defaultTabStop w:val="720"/>'
                '<w:footnotePr><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr><w:themeFontLang w:val="he-IL" w:bidi="he-IL"/>'
                '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    P = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                   '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
                   '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/></Types>')
        z.writestr('_rels/.rels', f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {P}><Relationship Id="rId1" Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr('word/document.xml', document)
        z.writestr('word/styles.xml', styles_xml())
        z.writestr('word/settings.xml', settings)
        z.writestr('word/footnotes.xml', footnotes)
        z.writestr('word/_rels/document.xml.rels', f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {P}>'
                   f'<Relationship Id="rIdStyles" Type="{R}/styles" Target="styles.xml"/><Relationship Id="rIdSettings" Type="{R}/settings" Target="settings.xml"/>'
                   f'<Relationship Id="rIdFootnotes" Type="{R}/footnotes" Target="footnotes.xml"/></Relationships>')
    print(f'raw docx written {out} | articles {len(arts)} | footnotes {len(notes.items)}')


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
