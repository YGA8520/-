"""Units of the booklet: which source pages, how they are titled, in which part they go.

kind:  exam    - questions (with ruled answer lines where the source has them)
       key     - questions followed by answers (תשובה)
       chavura - numbered question lists grouped by siman
       sheet   - dense question / answer sheet
`skip_head`: number of text lines at the top of the unit (after the standard noise is removed)
             that are replaced by title / sub / seal given here.
`form`: 'שם' (name + score) / 'הרב' (rabbi's name) / None
"""

PARTS = [
    dict(id='a', name='נטילת ידיים, ציצית וברכות השחר', sub='סימנים ד – מו', letter='א'),
    dict(id='b', name='ברכת התורה ופסוקי דזמרה', sub='סימנים מז – נז', letter='ב'),
    dict(id='c', name='קריאת שמע', sub='סימנים סא – עו', letter='ג'),
    dict(id='d', name='חבורות: קריאת שמע ותפילה', sub='סימנים ס – קח', letter='ד'),
    dict(id='e', name='דפי שאלות ותשובות', sub='סימנים עג – קב', letter='ה'),
]

# order in this list == order in the booklet
UNITS = [
    # ---------------- part a ----------------
    dict(id='u01', part='a', pages=(1, 2), kind='exam', kicker='מבחן', title='סימן ד׳', sub='נטילת ידיים שחרית',
         seal='ד', form='שם', skip_head=1),
    dict(id='u04', part='a', pages=(9, 10), kind='exam', kicker='מבחן', title='סימן ד׳', sub='נטילת ידיים',
         seal='ד', form='שם', skip_head=1, note='title_missing_siman'),
    dict(id='u02', part='a', pages=(3, 4), kind='key', kicker='דף שאלות ותשובות', title='הלכות נטילת ידיים שחרית', sub='סימן ד׳',
         seal='ד', form=None, skip_head=2),
    dict(id='u03', part='a', pages=(5, 8), kind='key', kicker='מבחן', title='הלכות ציצית ועטיפתו', sub='סימן ח׳ · מסעיף א׳ עד סעיף י״ד',
         org='כולל ערב ברומו של עולם', seal='ח', form='שם', skip_head=3),
    dict(id='u05', part='a', pages=(11, 12), kind='exam', kicker='מבחן', title='הלכות ברכות השחר', sub='סימן מו׳',
         seal='מו', form='שם', skip_head=1),
    # ---------------- part b ----------------
    dict(id='u06', part='b', pages=(15, 23), kind='exam', kicker='מבחן', title='סימנים מ״ז – נ״ז', sub='ברכת התורה, פרשת התמיד, פסוקי דזמרה',
         seal='מז–נז', form='שם', skip_head=1),
    dict(id='u07', part='b', pages=(24, 25), kind='exam', kicker='מבחן', title='סימנים מ״ח – מ״ט – נ׳', sub=None,
         seal='מח–נ', form='הרב', skip_head=1),
    dict(id='u08', part='b', pages=(26, 27), kind='exam', kicker='מבחן', title='סימנים נ״א – נ״ב – נ״ד', sub=None,
         seal='נא–נד', form='הרב', skip_head=1),
    dict(id='u09', part='b', pages=(28, 29), kind='exam', kicker='מבחן', title='סימן נ״ה', sub='סעיפים י״ג – י״ט',
         seal='נה', form='הרב', skip_head=1),
    dict(id='u29', part='b', pages=(79, 80), kind='exam', kicker='מבחן', title='סימנים רט״ו, נ״ג', sub='סעיפים א׳ – ט׳',
         seal='נג', form='הרב', skip_head=1, note='siman_215_check'),
    # ---------------- part c ----------------
    dict(id='u10', part='c', pages=(30, 31), kind='exam', kicker='מבחן', title='סימן סא', sub=None, org='ברומו של עולם',
         seal='סא', form='שם', skip_head=1),
    dict(id='u35', part='c', pages=(97, 98), kind='key', kicker='תשובות', title='סימן סא', sub='שאלות ותשובות למבחן',
         seal='סא', form=None, skip_head=0, qa_unlabelled=True),
    dict(id='u11', part='c', pages=(32, 33), kind='exam', kicker='מבחן', title='סימן סב', sub=None, org='ברומו של עולם',
         seal='סב', form='שם', skip_head=1),
    dict(id='u12', part='c', pages=(34, 35), kind='exam', kicker='מבחן חזרה', title='סימנים נה – סא', sub='(כולל)',
         seal='נה–סא', form='שם', skip_head=1),
    dict(id='u13', part='c', pages=(36, 37), kind='exam', kicker='מבחן חזרה', title='סימנים סב – סט', sub=None,
         seal='סב–סט', form='שם', skip_head=1),
    dict(id='u14', part='c', pages=(38, 39), kind='exam', kicker='מבחן', title='סימן סג', sub=None,
         seal='סג', form='שם', skip_head=1),
    dict(id='u15', part='c', pages=(40, 44), kind='key', kicker='תשובות', title='סימן סג', sub='שאלות ותשובות למבחן',
         seal='סג', form=None, skip_head=0),
    dict(id='u16', part='c', pages=(45, 46), kind='exam', kicker='מבחן', title='סימנים סד – סה', sub=None,
         seal='סד–סה', form='שם', skip_head=1),
    dict(id='u18', part='c', pages=(49, 50), kind='exam', kicker='מבחן', title='סימן סו', sub=None,
         seal='סו', form='שם', skip_head=1),
    dict(id='u19', part='c', pages=(51, 52), kind='exam', kicker='מבחן', title='סימן סו סעיפים ט, י', sub='וסימנים סז – סח',
         seal='סו–סח', form='שם', skip_head=2),
    dict(id='u20', part='c', pages=(53, 54), kind='exam', kicker='מבחן', title='סימן סט', sub=None,
         seal='סט', form='שם', skip_head=1),
    dict(id='u36', part='c', pages=(99, 100), kind='exam', kicker='מבחן', title='סימן ע׳', sub=None,
         seal='ע', form='שם', skip_head=1),
    dict(id='u21', part='c', pages=(55, 55), kind='exam', kicker='מבחן', title='סימן עא', sub='אבל והעוסקים במת פטורים מקריאת שמע',
         seal='עא', form='שם', skip_head=2),
    dict(id='u21b', part='c', pages=(56, 56), kind='exam', kicker='מבחן', title='סימן עא', sub=None,
         seal='עא', form='שם', skip_head=1),
    dict(id='u22', part='c', pages=(58, 58), kind='exam', kicker='מבחן', title='סימנים עב – עד', sub=None,
         seal='עב–עד', form='שם', skip_head=1),
    dict(id='u32', part='c', pages=(87, 87), kind='exam', kicker='מבחן', title='סימנים עג – עד', sub=None,
         seal='עג–עד', form='שם', skip_head=1),
    dict(id='u32k', part='c', pages=(65, 65), kind='key', kicker='תשובות', title='סימנים עג – עד', sub='שאלות ותשובות למבחן',
         seal='עג–עד', form=None, skip_head=1, bold_answers=True),
    dict(id='u26', part='c', pages=(68, 68), kind='exam', kicker='מבחן', title='סימן עו', sub='סעיף ו׳',
         seal='עו', form='שם', skip_head=2, manual='u26'),
    # ---------------- part d ----------------
    dict(id='u30', part='d', pages=(85, 86), kind='chavura', kicker='חבורה בהלכות קריאת שמע', title='מבחן קריאת שמע', sub='סימנים ס – סד · אלול תשפ״ה · עזרת נשים החדש',
         seal='ס–סד', form='שם', skip_head=4),
    dict(id='u17', part='d', pages=(47, 48), kind='chavura', kicker='חבורה בהלכות קריאת שמע', title='מבחן בהלכות קריאת שמע', sub='סימנים סה – עב, נח · חורף תשפ״ו · עזרת נשים החדש',
         seal='סה–עב', form='שם', skip_head=4),
    dict(id='u25', part='d', pages=(66, 67), kind='chavura', kicker='חבורה בהלכות קריאת שמע', title='מבחן קריאת שמע', sub='סימנים עג – עו · קיץ תשפ״ה · עזרת נשים החדש',
         seal='עג–עו', form='שם', skip_head=4),
    dict(id='u27', part='d', pages=(69, 70), kind='chavura', kicker='חבורה בהלכות קריאת שמע', title='מבחן קריאת שמע', sub='סימנים עז – פב · קיץ תשפ״ה · עזרת נשים החדש',
         seal='עז–פב', form='שם', skip_head=4),
    dict(id='u31', part='d', pages=(88, 89), kind='chavura', kicker='חבורה בהלכות קריאת שמע', title='מבחן קריאת שמע', sub='סימנים פג – פז · קיץ תשפ״ה · עזרת נשים החדש',
         seal='פג–פז', form='שם', skip_head=4),
    dict(id='u33', part='d', pages=(90, 93), kind='chavura', kicker='חבורה בהלכות תפילה', title='מבחן תפילה', sub='סימנים פט – צה · חורף תשפ״ו · עזרת נשים החדש',
         seal='פט–צה', form='שם', skip_head=4),
    dict(id='u34', part='d', pages=(94, 96), kind='chavura', kicker='חבורה בהלכות תפילה', title='מבחן הלכות תפילה', sub='סימנים צח – קח · קיץ תשפ״ו · עזרת נשים החדש',
         seal='צח–קח', form='שם', skip_head=4),
    # ---------------- part e ----------------
    dict(id='u37', part='e', pages=(71, 78), kind='sheet', kicker='דף שאלות ותשובות', title='סימנים עג – קב', sub=None,
         seal='עג–קב', form=None, skip_head=0, qa_unlabelled=True),
]

# pages that are exact (or superseded) copies and are left out of the booklet
DROPPED = [
    ((13, 14), 'עותק כפול של עמ׳ 11–12 (מבחן ברכות השחר סימן מו)'),
    ((57, 57), 'עותק כפול של עמ׳ 55 (מבחן סימן עא)'),
    ((59, 59), 'טיוטה קודמת של עמ׳ 87 (מבחן סי׳ עג–עד); עמ׳ 87 מלא יותר'),
    ((64, 64), 'עותק כפול של עמ׳ 58 (מבחן סי׳ ע״ב–ע״ד)'),
    ((60, 63), 'גרסה קודמת של עמ׳ 71–74 (דף שאלות ותשובות סימנים עג–עט); הגרסה המאוחרת נשארה'),
    ((81, 82), 'עותק כפול של עמ׳ 79–80 (מבחן סימנים רט״ו, נ״ג)'),
    ((83, 84), 'עותק כפול של עמ׳ 47–48 (חבורה בהלכות קריאת שמע)'),
    ((101, 102), 'עותק כפול של עמ׳ 99–100 (מבחן סימן ע)'),
]
