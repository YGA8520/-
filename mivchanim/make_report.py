#!/usr/bin/env python3
"""Editing report (Hebrew PDF): what was done, pages removed, assumptions, source irregularities."""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'design'))
from manifest import UNITS, DROPPED, PARTS
from common import font_face_css, hebrew_num

L = json.load(open(os.path.join(ROOT, 'build', 'layout.json')))
pm = L['pages_map']

drop_rows = ''.join(f'<tr><td><span dir="ltr">{a}–{b}</span></td><td>{w}</td></tr>' if a != b else f'<tr><td>{a}</td><td>{w}</td></tr>' for (a, b), w in DROPPED)
unit_rows = ''
for p in PARTS:
    for u in UNITS:
        if u['part'] == p['id']:
            a, b = u['pages']
            src = f'{a}–{b}' if a != b else str(a)
            unit_rows += f'<tr><td>{hebrew_num(pm[u["id"]])}</td><td>{u["kicker"]}</td><td>{u["title"]}{(" · " + u["sub"]) if u.get("sub") and u["kind"] != "chavura" else ""}</td><td><span dir="ltr">{src}</span></td></tr>'

typos = [
    ('עמ׳ 1', 'נתין (ניתן) · ראושנים / הראושנים (ראשונים) · הברה (הברכה) · נוכן (נכון) · הםא (האם) · לניטלת (לנטילת)'),
    ('עמ׳ 9–10', 'ניהיה (נהיה)'),
    ('עמ׳ 11', 'השטות (השיטות) · מסיומות / מסיום (מסוימות / מסוים)'),
    ('עמ׳ 58', 'הדיו (הדין)'),
    ('עמ׳ 65', 'ומתר · מתר.והראש · כןומדינה · שריואינו · ממט · בעינל טוחות · להית – מילים מחוברות או משובשות'),
    ('עמ׳ 66–67', 'באששית (בעששית)'),
    ('עמ׳ 71–78', 'איסוא (איסורא) · בזהטפח (בזה טפח)'),
]

html = f'''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>דוח עריכה</title><style>
{font_face_css('../assets/fonts')}
@page{{size:A4;margin:20mm 20mm 18mm}}
body{{font-family:'Frank',serif;font-weight:500;font-size:11pt;line-height:1.55;color:#16181d;direction:rtl}}
h1{{font-family:'Suez',serif;font-weight:400;font-size:24pt;color:#14264a;margin:0 0 2mm}}
h2{{font-family:'Suez',serif;font-weight:400;font-size:14pt;color:#14264a;margin:7mm 0 2mm;border-bottom:.3mm solid #c9a24b;padding-bottom:1mm}}
table{{border-collapse:collapse;width:100%;font-size:10pt}} td,th{{border-bottom:.2mm solid #ddd3b5;padding:1.1mm 2mm;text-align:right;vertical-align:top}}
th{{font-family:'Heebo',sans-serif;font-size:8.6pt;color:#a8802f}}
ul{{margin:1mm 0;padding-right:5mm}} li{{margin:0 0 1.2mm}}
.box{{background:#f6f2e7;border-right:1.1mm solid #c9a24b;padding:2.4mm 4mm;margin:2mm 0}}
</style></head><body>
<h1>דוח עריכה – מבחני הסימנים</h1>
<div>מה נעשה בקובץ, מה הוסר, ומה כדאי לאשר לפני הדפסה.</div>

<h2>1. מה נעשה</h2>
<ul>
<li>כל תוכן המקור (102 עמודים) הוקלד מחדש בעיצוב אחיד: כותרת פתיחה עם חותם הסימן, שדה שם וציון, שאלות עם אות/מספר בעיגול, שורות כתיבה, תשובות בלוח מובחן, כותרת עליונה ומספור עמודים באותיות.</li>
<li>הטקסט לא שונה. נבדק אוטומטית: כל מילה במקור מופיעה בקובץ החדש, ואין מילים שנוספו. החריגים היחידים הם נוסחי הברכה "בהצלחה" שאוחדו (ראו סעיף 4).</li>
<li>נוספו: שער, שער פנימי, עמוד קרדיטים, תוכן עניינים (משמש גם כיומן ציונים), חמישה עמודי פתיחה לחלקים ושער אחורי.</li>
<li>סדר החוברת: ממוין לפי סימן בתוך חמישה חלקים (במקור הסדר היה לפי הוספת הקבצים). מבחן ודף התשובות שלו הועמדו זה אחר זה.</li>
</ul>

<h2>2. עמודים שהוסרו</h2>
<div>שמרתי עותק אחד מכל תוכן כפול (כפי שאושר). המקור נשאר בריפו ב-<span dir="ltr">mivchanim/src/all-tests.pdf</span>.</div>
<table><tr><th>עמודים במקור</th><th>סיבה</th></tr>{drop_rows}</table>

<h2>3. דברים לאישור</h2>
<div class="box"><ul>
<li><b>עמ׳ 9–10 במקור:</b> הכותרת "מבחן סי׳" ללא מספר סימן. הוצג כ"סימן ד׳" לפי תוכן השאלות (נטילת ידיים, שו״ע סעיף כב ורמב״ם). נא לאשר.</li>
<li><b>עמ׳ 79–82 במקור:</b> "מבחן על סימנים רט״ו, נ״ג". ייתכן שצריך להיות קט״ו; הושאר כפי שכתוב.</li>
<li><b>כותרות משנה ושמות החלקים</b> (למשל "ברכת התורה, פרשת התמיד, פסוקי דזמרה") הוסיפו מטעמי ארגון; ניתנות לשינוי בקובץ <span dir="ltr">design/manifest.py</span>.</li>
<li><b>עמ׳ 59 במקור</b> (מבחן סי׳ עג–עד, 6 שאלות) הוסר כטיוטה קודמת של עמ׳ 87, שמכיל גרסה מעודכנת (שאלה 3 שונה).</li>
<li><b>עמ׳ 60–63 במקור</b> הוסרו כגרסה קודמת של 71–74; התוכן זהה פרט לתיקונים קלים (למשל "אץ" → "א").</li>
<li>עמודי קרדיטים: הפרטים (מייל, טלפונים, קו בית הוראה, נדרים פלוס) הועתקו מהחוברת הקודמת של הארגון.</li>
</ul></div>

<h2>4. שינויים טיפוגרפיים בלבד</h2>
<ul>
<li>נוסחי הסיום אוחדו: "ב ה צ ל ח ה ! !", "בהצלחה!!" → "בהצלחה!". בעמודי החבורה הופיע "הצלחה רבה!" ללא ב׳ והושלם ל"בהצלחה רבה!".</li>
<li>שורות "שם / ציון / הרב" ו"בס״ד" שהיו בראש כל מקור הוחלפו בשדה אחיד ובכותרת העמוד. "ציון ____" בסוף עמ׳ 8 הוסר כי השדה עבר לראש היחידה.</li>
<li>נקודה בודדה שהופיעה בין שורות בעמ׳ 92 במקור הוסרה.</li>
<li>תיוג השאלות (א׳, ב׳ / 1, 2) נשמר כפי שהוא, והסוגריים/המירכאות כפי שהוקלדו.</li>
</ul>

<h2>5. שגיאות כתיב שנשארו במקור (לא תוקנו)</h2>
<div>לא תיקנתי טקסט הלכתי ללא אישור. להלן דוגמאות בולטות; מומלץ מעבר הגהה לפני הדפסה.</div>
<table><tr><th>מקום</th><th>דוגמאות</th></tr>{''.join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a, b in typos)}</table>

<h2>6. תוכן החוברת</h2>
<table><tr><th>עמוד</th><th>סוג</th><th>כותרת</th><th>עמ׳ במקור</th></tr>{unit_rows}</table>
</body></html>'''
open(os.path.join(ROOT, 'build', 'report.html'), 'w', encoding='utf8').write(html)
json.dump([dict(html='build/report.html', pdf='output/דוח-עריכה.pdf')], open(os.path.join(ROOT, 'build', 'job_report.json'), 'w'))
subprocess.run(['node', os.path.join(ROOT, 'tools', 'render.js'), os.path.join(ROOT, 'build', 'job_report.json')], check=True, cwd=ROOT)
