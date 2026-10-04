# Next task (requested by the client; run this in a LOCAL session on the client's Windows machine)

Read `README.md` first (pipeline, design decisions, how to run). Work on branch `claude/text-styling-format-crr1qi`.
The client speaks Hebrew – report in Hebrew, short and concrete.

## 1. Add every חבורה from the client's folder – without duplicates
Folder: `C:\Users\YGA\Desktop\זאדה\חבורות`  (many .docx files; some are already in the booklet, see `src_names.json` and `book.py`).
* Inventory first: list every .docx (name, modified date, words, first lines). Find which are already in the booklet and which are new.
* Duplicate check at the **text** level (normalise: drop quotes/punctuation, split to words, `difflib.SequenceMatcher`): identical = skip; a near-identical or newer version of an article already in the booklet → the client's rule: **keep the more up-to-date text** (judge by content and structure, not only by file date; report the reasoning and what differs). Never silently drop text.
* Previous decisions: `f01`, `f05`–`f09` are duplicates of the compilation `f17` (skipped); for "דין כוונת הברכות" the compilation version is used over `f04`.
* New articles: extend `book.py` (`EXTRA` entries or an automatic reader of title / author / siman from each file). Rules: add שליט״א after author names; siman order with divider pages; the title in the frame; footnotes lettered per article.
* After building: `build.js` must print `word check ... differences 0` and `hanging indent ... misaligned 0, column-top 0`. Regenerate the PDF/DOCX and `make_notes.py`.

## 2. Fonts – choose from `C:\Windows\Fonts` (by your own judgment, then show a comparison page)
Use installed family names in `config.json` → `fonts` (and `wordFonts` for Word); no font files in git unless freely licensed.
Roles (see README):
* `body` – readable, beautiful, dignified, suited to continuous Torah reading (running text, 12/17 pt).
* `lead` – a more dignified face for the bold first word of each paragraph and for sub-headings.
* `display` – calligraphic, for article titles / divider pages / ToC headings.
* `notes` – light weight, for the footnotes ("הערות וציונים"; set `type.foot.weight`).
* `author` – an interesting face for the author's name.
Check with fontTools that the chosen fonts really contain Hebrew **with niqqud/ta'amim if needed and the geresh/gershayim (׳ ״)**, and have a bold (or a heavy) weight where used bold. Render a one-page comparison (same paragraph, title, footnote, author line) for the chosen set vs the current one (Frank Ruhl Libre / David Libre), pick the best, rebuild everything, compare page count and `loose lines` (engine stats in `out/book.layout.json`), and look at several pages before delivering.

## 3. Still open
Cover page (the client will send a file; leave for the end). Unbalanced brackets: not to be fixed for now.
