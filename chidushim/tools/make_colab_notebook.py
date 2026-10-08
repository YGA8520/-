#!/usr/bin/env python3
"""Build colab_transcribe.ipynb from transcribe_ivrit.py, so the notebook always carries exactly the script that was tested."""
import json, os

here = os.path.dirname(os.path.abspath(__file__))
script = open(os.path.join(here, 'transcribe_ivrit.py'), encoding='utf-8').read()


def md(text):
    return dict(cell_type='markdown', metadata={}, source=text.strip('\n').splitlines(True))


def code(text):
    return dict(cell_type='code', metadata={}, execution_count=None, outputs=[], source=text.strip('\n').splitlines(True))


cells = [
    md('''
# תמלול שני להקלטות הלימוד

המחברת הזאת מתמללת את כל ההקלטות פעם נוספת, במודל חזק לעברית, כדי שאפשר יהיה להשוות מול התמלול של "אלף בוט". אין צורך להבין קוד.

**מה עושים (4 צעדים)**
1. **בדרייב:** יוצרים תיקייה בשם `shiurim` (באותיות אנגליות) ומעלים אליה את כל ההקלטות.
2. **למעלה בתפריט:** זמן ריצה ← שנה סוג זמן ריצה ← בוחרים **T4 GPU** ← שמירה.
3. **למעלה בתפריט:** זמן ריצה ← **הפעל הכול**. כשקופצת בקשה לגשת לדרייב, מאשרים.
4. ממתינים. הלשונית צריכה להישאר פתוחה, והמחשב דלוק.

תא 3 מתמלל 5 דקות לדוגמה ומדפיס אותן, ואז תא 4 ממשיך לכל ההקלטות. אם הדוגמה נראית גרועה, עוצרים (זמן ריצה ← הפסק ביצוע) ושולחים לי אותה.
אם החיבור נותק באמצע — שוב **הפעל הכול**. מה שכבר תומלל לא יחושב מחדש.

התוצאות נשמרות בדרייב בתיקייה `shiurim_transcripts`.
'''),
    code('''
# תא 1: בדיקת כרטיס מסך והתקנה
!nvidia-smi -L
# av חייב להיות מתחת ל-17 — עם גרסה חדשה faster-whisper 1.2.1 נכשל בקריאת קבצי שמע
!pip install -q faster-whisper==1.2.1 "av<17"
'''),
    code('''
# תא 2: חיבור לדרייב והגדרת תיקיות (אין צורך לשנות כלום)
from google.colab import drive
drive.mount('/content/drive')

AUDIO_DIR = '/content/drive/MyDrive/shiurim'               # תיקיית ההקלטות
OUT_DIR   = '/content/drive/MyDrive/shiurim_transcripts'   # לכאן ייכתבו התמלולים
MODEL     = 'ivrit-ai/whisper-large-v3-turbo-ct2'          # מהיר. לדיוק מרבי (איטי בערך פי 2): 'ivrit-ai/whisper-large-v3-ct2'
'''),
    code('%%writefile /content/transcribe_ivrit.py\n' + script),
    md('''
## בדיקה קצרה (5 דקות)
מתמללת רק 5 הדקות הראשונות של ההקלטה הראשונה, לתיקייה נפרדת, ומדפיסה אותן.
'''),
    code('''
# תא 3: בדיקה
!python -u /content/transcribe_ivrit.py --input "{AUDIO_DIR}" --output "{OUT_DIR}_test" --model {MODEL} --limit 1 --clip-seconds 300
import glob
for p in sorted(glob.glob(f"{OUT_DIR}_test/*.txt")):
    print("=====", p); print(open(p, encoding="utf-8").read()[:3000])
'''),
    md('''
## הרצה מלאה
זה לוקח כמה שעות, תלוי באורך ההקלטות. הלשונית צריכה להישאר פתוחה.
'''),
    code('''
# תא 4: כל ההקלטות
!python -u /content/transcribe_ivrit.py --input "{AUDIO_DIR}" --output "{OUT_DIR}" --model {MODEL}
'''),
    code('''
# תא 5: סיכום. את run_log.txt (קובץ קטן) אפשר לשלוח לבדיקה
import glob, os
done = len(glob.glob(f"{OUT_DIR}/*.json"))
print("תומללו:", done, "| שגיאות:", os.path.exists(f"{OUT_DIR}/errors.log"))
print(open(f"{OUT_DIR}/run_log.txt", encoding="utf-8").read()[-3000:])
'''),
]

nb = dict(cells=cells, metadata=dict(accelerator='GPU', colab=dict(provenance=[], gpuType='T4'),
                                     kernelspec=dict(name='python3', display_name='Python 3'),
                                     language_info=dict(name='python')),
          nbformat=4, nbformat_minor=0)
out = os.path.join(here, 'colab_transcribe.ipynb')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print('wrote', out)
