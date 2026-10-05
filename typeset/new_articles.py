#!/usr/bin/env python3
"""The additional חבורות (folder "חבורות"): a manifest of every article that is added to the booklet, loaded through the same
classifier as the first batch.  The choice of versions (what is a duplicate of what, which version is newest) is documented in
DECISIONS at the bottom and printed by `python new_articles.py --report`.

Source folder: $HAVUROT_DIR, or ./src/חבורות, or (cloud session) the scratchpad copy.
"""
import json, os, re, sys, unicodedata
from ingest import load, doc_default_size
import book
from book import classify_items, used_footnotes, honorific
from parse_docx import fix_quotes
import compile_split

HERE = os.path.dirname(os.path.abspath(__file__))
HAV = os.environ.get('HAVUROT_DIR') or next((d for d in (os.path.join(HERE, 'src', 'חבורות'), os.path.join(HERE, 'src_havurot'),
        '/tmp/claude-0/-home-user--/e48d2585-9ec4-5df3-ad1f-53def33d6015/scratchpad/hav/חבורות') if os.path.isdir(d)), os.path.join(HERE, 'src', 'חבורות'))

_NF = lambda x: unicodedata.normalize('NFC', x).replace('‎', '').replace('‏', '').strip()


def hav_path(name):
    if not os.path.isdir(HAV):
        raise SystemExit('folder with the additional חבורות not found: %s (set HAVUROT_DIR)' % HAV)
    have = {_NF(f): f for f in os.listdir(HAV)}
    if _NF(name) not in have:
        raise SystemExit('missing file: %s in %s' % (name, HAV))
    return os.path.join(HAV, have[_NF(name)])


def gem(n):
    """gematria of a siman / se'if number: 8 -> ח׳, 18 -> י״ח, 489 -> תפ״ט"""
    vals = ((400, 'ת'), (300, 'ש'), (200, 'ר'), (100, 'ק'), (90, 'צ'), (80, 'פ'), (70, 'ע'), (60, 'ס'), (50, 'נ'), (40, 'מ'), (30, 'ל'),
            (20, 'כ'), (10, 'י'), (9, 'ט'), (8, 'ח'), (7, 'ז'), (6, 'ו'), (5, 'ה'), (4, 'ד'), (3, 'ג'), (2, 'ב'), (1, 'א'))
    out = ''
    while n > 0:
        if n in (15, 16):
            out += 'טו' if n == 15 else 'טז'
            break
        for v, ch in vals:
            if n >= v:
                out += ch
                n -= v
                break
    return out[:-1] + '״' + out[-1] if len(out) > 1 else out + '׳'


def label(siman, seif=None, extra=''):
    s = 'סימן ' + gem(siman)
    if seif:
        s += ' סעיף ' + gem(seif)
    return s + extra


# Each entry: file (single docx) or mtk (title inside "חוברת מתוקנת"); head = number of leading non-empty paragraphs that are header
# lines (author / month / phone / title ...) and are removed; title/author/subtitle explicit; siman/seif for the order.
# 'by' documents where author or title is not in the file (see DECISIONS).
S = lambda **k: dict(k, src='file')
M = lambda **k: dict(k, src='mtk')
MANIFEST = [
    # ---- סימן ד
    S(file='ברכת על נטילת ידים הרב משה זאדד.docx', head=2, title='ברכת על נטילת ידים', author='הרב משה זאדה', siman=4),
    # ---- סימן ה
    S(file='‏‏__בענין הזכרת וכונת שם השם - עותק (2) - עותק.docx', head=2, title='הזכרת השם', subtitle='קונטרס', author='הרב משה זאדה', siman=5),
    # ---- סימן ו
    M(mtk='נוסח ברכת אשר יצר ופירושה', author='אברהם יהונתן ניסן', siman=6),
    # ---- סימן ח
    M(mtk='בדין פשיטת הטלית', author='אברהם יהונתן ניסן', siman=8, seif=0),
    S(file='סימן ח (4).docx', head=3, title='בענין ברכת ציצית והעטיפה מעומד', author='נח קליין', siman=8, seif=1),
    S(file='סימן ח.docx', head=3, title='אופן אמירת ברכת המצות', author='הרב משה זאדה', siman=8, seif=6),
    S(file='בענין בדיקת הציציות ובדין של סמיכה על החזקה סימן ח סעיף ט.docx', head=1, title='בענין בדיקת הציציות ובדין של סמיכה על החזקה', author='', siman=8, seif=9),
    S(file='סימן ח (3).docx', head=2, title='בענין להוציא אחרים בברכת שהחיינו', author='אלרועי משה דדוש', siman=8, seif=10),
    S(file='סימן ח (2).docx', head=2, title='בענין הפסק בלבישת כמה בגדים', author='אליעזר רוטנברג', siman=8, seif=12),
    S(file='סימן ח אליעזר רוטנברג.docx', head=2, title='סיכום השיטות בפשט טליתו', author='אליעזר רוטנברג', siman=8, seif=14),
    S(file='נפלה טליתו הרב חיים גרינולד.docx', head=2, title='בדין נפלה טליתו', author='הגאון הרב חיים פרץ גרינוולד', siman=8, seif=15),
    # ---- סימן יח
    S(file='בענין ציצית בלילה.docx', head=2, title='מתי מתחיל זמן מצות ציצית', author='הרב משה זאדה', siman=18, seif=3),
    S(file='סימן יח (2).docx', head=2, title='בעניין מח׳ רא״ש ורמב״ם בזמן מצוות ציצית', author='אלרועי משה דדוש', siman=18, seif=3),
    S(file='סימן יח אליעזר רוטנברג.docx', head=1, title='סיכום השיטות בזמן ציצית', author='אליעזר רוטנברג', siman=18, seif=3),
    S(file='סימן יח.docx', head=2, title='הלכות ציצית', author='אברהם גוטמן', siman=18, seif=23),
    # ---- סימן מז
    S(file='__ספק בירך 2) - עותק.docx', head=1, title='ספק בירך ברכת התורה', author='', siman=47, seif=0),
    S(file='חיוב ברכת התורה (2).docx', head=1, title='חיוב ברכת התורה לחתן בר מצוה', author='', siman=47, seif=0),
    S(file='סימן מז - וייס.docx', head=1, title='בענין שינת קבע בלילה לברכת התורה', author='הרב וייס', siman=47, seif=12),
    # ---- סימן מח
    S(file='סימן מח.docx', head=2, title='גדר ענין תפילות כנגד תמידין תקנום', author='', siman=48),
    # ---- סימן נא / נג / נה / נו
    M(mtk='פסוקי דזמרה דאורייתא או דרבנן', author='משה דוד הופט', siman=51),
    S(file='משה דוד הופט סימן נג סעיף א.docx', head=3, title='בעניין עמידה בברכת ישתבח', author='משה דוד הופט', siman=53, seif=1),
    M(mtk='בעניין הפסק בפסוד״ז', author='יעקב גדליהו אייזנשטיין', siman=53, seif=1),
    M(mtk='בעניין גדר דבר שבקדושה בעשרה', author='יעקב גדליהו אייזנשטיין', siman=55, seif=1),
    M(mtk='סיכום השיטות דאין אומרים דבר שבקדושה בפחות מעשרה', author='משה דוד הופט', siman=55, seif=1),
    S(file='חוברת סימן נה.docx', rng=(0, 23), head=3, title='החששות שיש לחוש מנייני הקורונה', author='אברהם יהונתן ניסן', siman=55, seif=14),
    S(file='חוברת סימן נה.docx', rng=(23, None), head=2, title='בעניין רשויות חולקות לצירוף עשרה', author='יעקב ישראל שטרן', siman=55, seif=19),
    S(file='משה זאדה קדיש דרבנן סימן נו.docx', head=1, title='בענין קדיש דרבנן', author='הרב משה זאדה', siman=56),
    # ---- סימן נח
    S(file="בענין זמן קר''ש - זאדה.docx", head=2, title='זמן קריאת שמע של שחר מן המובחר', author='הרב משה זאדה', siman=58, seif=1),
    S(file='משה דוד הופט סימן נח סעיף א_1.docx', head=2, title='סיכום נקודות לסוגיית זמן קריאת שמע של שחרית', author='משה דוד הופט', siman=58, seif=1),
    S(file="בענין זמן קר''ש - סימן נח.docx", head=1, title='זמן קריאת שמע של שחר מן המובחר', author='', siman=58, seif=1),
    S(file='עזרא בטאט סימן נח סעיף א_5.docx', head=4, title='יבואר שדעת המשנה ברורה שחייבים לקרוא ק״ש בנץ החמה', author='עזרא בטאט', siman=58, seif=1),
    S(file='עזרא בטאט סימן נח סעיף ה_1.docx', head=4, title='אם זמני ק״ש תלויים בשכיבה ובקימה בלבד או גם ביום ולילה', author='עזרא בטאט', siman=58, seif=5),
    S(file='סימן נח.docx', head=1, title='בענין סוף זמן בק״ש', author='', siman=58, seif=6),
    S(file='חוברת סימן נח.docx', head=3, title='בענין עניית אמן באמצע הברכה', author='אברהם יהונתן ניסן', siman=58, seif=1),
    # ---- סימן נט
    S(file='נח קליין סימן נט סעיף ב.docx', head=2, title='דיני טעה בברכת יוצר', author='נח קליין', siman=59, seif=2),
    S(file='אליעזר רוטנברג סימן נט סעיף ב.docx', head=0, title='דיני טעה בברכת יוצר', author='אליעזר רוטנברג', siman=59, seif=2),
    S(file='סימן נט רוטנברג.docx', head=3, title='בגדר ברכות ק״ש וברכות ק״ש אין מעכבות זו את זו', author='אליעזר רוטנברג', siman=59, seif=4),
    S(file='עזרא בטאט סימן נט סעיף ד.docx', head=4, title='בירור דעת מרן השולחן ערוך בדין עניית אמן אחר ברכת הבוחר בעמו ישראל', author='עזרא בטאט', siman=59, seif=4),
    # ---- סימן ס
    S(file='אליעזר רוטנברג סימן ס סעיף ד.docx', head=2, title='הגדרת מחלוקת השיטות במצוות צריכות כונה ועפי״ז להבין הדינים שמצאנו בפוסקים', author='אליעזר רוטנברג', siman=60, seif=4),
    S(file='יעקב ישראל שטרן סימן ס סעיף ד.docx', head=2, title='ביסוד הדין דמצוות צריכות כוונה', author='יעקב ישראל שטרן', siman=60, seif=4),
    S(file='נח קליין סימן ס סעיף ד.docx', head=1, title='מצוות צריכות כוונה', author='נח קליין', siman=60, seif=4),
    S(file='משה דוד הופט סימן ס סעיף ד.docx', head=2, title='סיכום משנ״ב סימן ס׳ סעיף ד׳', author='משה דוד הופט', siman=60, seif=4),
    S(file='מצוות צריכות כוונה (2).docx', head=3, title='בענין אם השומע ברכה מאחר יש לו לחוש דיצא יד״ח', author='יעקב ישראל שטרן', siman=60, seif=4),
    S(file='עזרא בטאט סימן ס סעיף ד.docx', head=4, title='אם בעת עשיית המצוה מכוון בעיקר לדבר אחר', author='עזרא בטאט', siman=60, seif=4),
    S(file='סימן ס סעיף ד ביאור הסוגיה בענין מצות צריכות כוונה.docx', head=0, title='ביאור הסוגיה בענין מצוות צריכות כוונה', author='נאור רוזין', siman=60, seif=4),
    S(file='סימן ס סעיף ד כוונת טעם המצוה.docx', head=1, title='בענין הכוונה של הטעם של המצוה', author='נאור רוזין', siman=60, seif=4),
    S(file='סימן ס סעיף ד עיקרי הדברים לספר בענין מצות צריכות כוונה נהור רוזין.docx', head=0, title='עיקרי הדברים לספר בענין מצוות צריכות כוונה', author='נאור רוזין', siman=60, seif=4),
    S(file='סימן ס משקרא קש אין צריך לברך שכבר נפטר באהבה רבה.docx', head=1, title='ברכת אברהם', subtitle=None, author='', siman=60, seif=0),
    # ---- סימן סא
    S(file='סימן סא (2).docx', head=2, title='בענין קבלת עול מלכות שמים', author='יעקב ישראל שטרן', siman=61, seif=1),
    S(file='בענין השלמת רמח תיבות בקריאת שמע.docx', head=1, title='בענין השלמת רמ״ח תיבות בקר״ש', author='הרב נאור רוזין', siman=61, seif=3),
    S(file='סימן סא.docx', head=2, title='בענין השלמת רמ״ח תיבות בק״ש (סיכום)', author='', siman=61, seif=3),
    S(file='סימן סא סיכום השיטות בענין השלמת הרמח תיבות שבקש.docx', head=1, title='סיכום השיטות בענין השלמת הרמ"ח תיבות שבק"ש', author='הרב משה זאדה', siman=61, seif=3),
    S(file='עזרא בטאט סימן סא סעיף ט_2.docx', head=4, title='ש״ץ שלא כיון בפסוק ראשון דקריאת שמע, האם יחזור לאומרו', author='עזרא בטאט', siman=61, seif=9),
    # ---- סימן סב – ע
    S(file='עזרא בטאט סימן סב סעיף א_3.docx', head=5, title='דקדוק באותיותיה מהו', author='עזרא בטאט', siman=62, seif=1),
    S(file='__-סימן סג-קריאת   משה זאדה שמע.docx', head=2, title='בעניין עקירת חכמים מצוה דאורייתא', author='הרב משה זאדה', siman=63),
    S(file='עזרא בטאט סימן סג סעיף א .docx', head=5, title='לעמוד בקריאת שמע דערבית', author='עזרא בטאט', siman=63, seif=1),
    S(file='סימן סה בדין שהה לגמור את כולה.docx', head=1, title='בדין שהה לגמור את כולה', author='הרב משה זאדה', siman=65, seif=0),
    S(file='עזרא בטאט סימן סה סעיף א_4.docx', head=4, title='בדברי ביאור הלכה סימן סה ס״א ד״ה ׳קראה׳', author='עזרא בטאט', siman=65, seif=1),
    S(file='עזרא בטאט - סימן סו סעיף ד.docx', head=4, title='קראוהו לעלות לתורה שלא בפרהסיא בשעה שעוסק בקריאת שמע וברכותיה, האם יעלה או שאין לחוש בזה לכבוד התורה', author='עזרא בטאט', siman=66, seif=4),
    S(file='עזרא בטאט סימן סז.docx', head=4, title='בענין חיוב זכירת יציאת מצרים אי מן התורה או מדרבנן', author='עזרא בטאט', siman=67),
    S(file='עזרא בטאט - סימן סט.docx', head=5, title='בדין רובו ככולו לצירוף מנין', author='עזרא בטאט', siman=69, seif=1),
    S(file='עזרא בטאט - חבורה סימן ע.docx', head=4, title='העוסק במלאכה או בשאר דברים האם צריך לפסוק לקריאת שמע?', author='עזרא בטאט', siman=70, seif=5),
    # ---- סימן קח, של״ד (יורה דעה), תפ״ט
    S(file='סימן קח - משה זאדה.docx', head=1, title='בענין תפילת תשלומין', author='הרב משה זאדה', siman=108),
    M(mtk='צירוף מנודה לדבר שבקדושה ולמגילה [ובעניין נידוי בזמן הזה]', author='עזרא בטאט', siman=334, seif=1, label_base='יורה דעה סימן של״ד'),
    M(mtk='בדין ספירת העומר קודם תפילת ערבית', author='אברהם יהונתן ניסן', siman=489),
]


_MTK = {}


def _mtk_units():
    if not _MTK:
        us, _ = compile_split.split_compile(hav_path('חוברת מתוקנת.docx'))
        _MTK['u'] = us
    return _MTK['u']


def _from_file(m):
    items, fns = load(hav_path(m['file']))
    D = doc_default_size(items)
    if m.get('rng'):                         # one file that holds several articles: [from, to) of the raw items
        items = items[m['rng'][0]:m['rng'][1]]
    body, k = [], 0
    for it in items:
        if it['k'] == 'p' and (not it['text'] or it.get('img')):
            continue
        if it['k'] == 'p' and k < m['head']:
            k += 1
            continue
        if it['k'] == 'p' and book.BASAD.match(it['text']) and len(it['text']) < 60:
            continue                         # running head "בס״ד <author>" repeated at the top of every printed page
        body.append(it)
    blocks, fn_out = classify_items(body, fns, D, loose_heads=True)
    return blocks, used_footnotes(blocks, fn_out)


def _from_mtk(m):
    for u in _mtk_units():
        if compile_split._close(u['title'], m['mtk']):
            return u['blocks'], u['footnotes']
    raise SystemExit('not found in the compilation: ' + m['mtk'])


NOTES = {   # file name (or title for entries taken from "חוברת מתוקנת") -> remark shown in the integration report
    'סימן מז - וייס.docx': 'בקובץ אין כותרת – הכותרת נוסחה מתוכן הקובץ; שם הרב וייס לפי שם הקובץ',
    'אליעזר רוטנברג סימן נט סעיף ב.docx': 'בקובץ אין כותרת – ניתנה אותה כותרת כמו למאמר של נח קליין באותו נושא',
    'חוברת סימן נח.docx': 'בקובץ אין כותרת – הכותרת נוסחה מתוכן הקובץ (התווית בקובץ: סימן נ״ח סעיף א׳)',
    'סימן ח (3).docx': 'הכותרת נלקחה מהחוברת ״בעריכה״; המחבר "הרב דדוש" בקובץ',
    'סימן סא.docx': 'סיכום קצר; נוסף ״(סיכום)״ לכותרת כדי להבדילו מהמאמר הארוך באותו נושא',
    'סימן ס סעיף ד עיקרי הדברים לספר בענין מצות צריכות כוונה נהור רוזין.docx': 'טיוטת ספר (כ-21,000 מילים); גרסה מעודכנת (אוקטובר 2026) במקום הגרסה הקודמת; המחבר לפי שם הקובץ (קודם יוחס בטעות לרב זאדה)',
    'סימן ס סעיף ד ביאור הסוגיה בענין מצות צריכות כוונה.docx': 'המחבר אינו מופיע בשם הקובץ או בגוף הטקסט – נקבע לפי מאפייני הקובץ (נאור רוזין) והמשכיות הסדרה בסימן ס׳ סעיף ד׳; השיוך אושר על ידי העורך',
    'סימן ס סעיף ד כוונת טעם המצוה.docx': 'המחבר אינו מופיע בשם הקובץ או בגוף הטקסט – נקבע לפי מאפייני הקובץ (נאור רוזין); ממשיך את ״עיקרי הדברים״ (״התבאר עד כה בהרחבה״); השיוך אושר על ידי העורך',
    'סימן ס משקרא קש אין צריך לברך שכבר נפטר באהבה רבה.docx': 'ללא מחבר בקובץ ובשמו (נשאר ללא מחבר, לפי הנחיית העורך); בראש הקובץ מופיעה הכותרת ״ברכת אברהם״ - היא כותרת המאמר, והשורה הראשונה של הטקסט נשארה בגוף המאמר',
    'סימן סא סיכום השיטות בענין השלמת הרמח תיבות שבקש.docx': 'ללא מחבר בקובץ ובשמו; המחבר - ראש הכולל הרב משה זאדה (לפי הנחיית העורך); טקסט שונה מ״סימן סא.docx״ באותו נושא – נכללו שניהם',
    'סימן סה בדין שהה לגמור את כולה.docx': 'ללא מחבר בקובץ ובשמו; המחבר - ראש הכולל הרב משה זאדה (לפי הנחיית העורך); ללא סעיף בשם הקובץ – הוצב בתחילת הסימן',
    'עזרא בטאט - סימן סט.docx': 'הוסרו שורות הכותרת: חודש החבורה ומספר טלפון',
    'סימן נח.docx': 'ללא מחבר בקובץ',
    'בענין זמן קר\'\'ש - סימן נח.docx': 'ללא מחבר בקובץ; כותרת זהה למאמר של הרב זאדה אך טקסט שונה',
    '\u200f\u200f__בענין הזכרת וכונת שם השם - עותק (2) - עותק.docx': 'שלוש גרסאות – נבחרה האחרונה (יוני 2026)',
    'בענין ציצית בלילה.docx': 'ארבע גרסאות – נבחרה האחרונה והמלאה (פברואר 2026)',
    'פסוקי דזמרה דאורייתא או דרבנן': 'סימן נ״א לפי הקשר (אין תווית בחוברת המתוקנת)',
}


def build_articles():
    arts = []
    for i, m in enumerate(MANIFEST):
        blocks, fn = _from_file(m) if m['src'] == 'file' else _from_mtk(m)
        siman, seif = m['siman'], m.get('seif')
        base = m.get('label_base') or ('סימן ' + gem(siman))
        lab = base + (' סעיף ' + gem(seif) if seif else '')
        title = fix_quotes(m.get('title') or m['mtk'].replace('׳', "'"))
        author = m.get('author', '')
        arts.append({'src': 'havurot', 'title': title, 'subtitle': m.get('subtitle'), 'author': honorific(author) if author else '',
                     'label': lab, 'blocks': blocks, 'footnotes': fn, 'siman': siman, 'seif': seif or 0, 'idx': 2000 + i,
                     'srcfile': m.get('file') or 'חוברת מתוקנת.docx', 'note': NOTES.get(m.get('file') or m.get('mtk'), '') or ('ללא מחבר בקובץ' if not author else '')})
    return arts


if __name__ == '__main__':
    arts = build_articles()
    tot = 0
    for a in arts:
        w = sum(len(''.join(r['t'] for r in b['runs']).split()) for b in a['blocks'] if b['t'] != 'tbl')
        h = sum(1 for b in a['blocks'] if b['t'] in ('h2', 'h3'))
        tot += w
        print('%-22s | %-50s | %-26s | blocks %3d heads %2d fn %2d words %5d' % (a['label'][:22], a['title'][:50], a['author'][:26], len(a['blocks']), h, len(a['footnotes']), w))
    print(len(arts), 'articles', tot, 'words')
