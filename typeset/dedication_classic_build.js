#!/usr/bin/env node
/* The dedication page, classic version: set like the dedication page of a printed sefer - black ink on white, centred lines with deliberate breaks, much white
 * space, a thin double rule round the page with the corner ornament of the booklet inside its corners, the small fleuron of the booklet above and below.
 * It differs from the other pages (a full frame instead of the two side rails, no grey bands) but uses only the fonts and ornaments of the booklet.
 *   node dedication_classic_build.js pages/<name>.json [out_dir]    ->  out_dir/<id>-classic.pdf, out_dir/<id>-classic.png
 * Fonts as in dedication_gold_build.js: assets/fonts, ../font-library/my-fonts/fonts, $FONT_DIR. EFT Algebra (the name of the booklet, as on the cover of
 * Ritcha), Guttman Mantova Decor (the name of the donor), Guttman Mantova (the blessing, the verse, הי״ו), Livorna (the small lines), HadasaNew (the signature). */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const MM = 96 / 25.4;
const T = { w: 176, h: 250, x0: 17, x1: 159, top: 5.5, bottom: 241 };          // page, the free area between the silver rails of the haskamot (mm)
const DIRS = [path.join(__dirname, 'assets', 'fonts'), path.join(__dirname, '..', 'font-library', 'my-fonts', 'fonts'), process.env.FONT_DIR].filter(Boolean);
const NOQ = 'U+0000-05F2,U+05F5-10FFFF';
const FACES = [
  ['Ded Title', 400, ['CALIG.TTF', 'ashkenazyregular.ttf'], 'StamAshkenazCLM.ttf'],
  ['Ded Name', 400, ['EFT_Pnina Decor.ttf', 'ashkenazyregular.ttf'], 'StamAshkenazCLM.ttf'],
  ['Ded Text', 700, ['EFT_Pnina Bold.ttf', 'פרנק בולד.otf'], 'FrankRuhlLibre.ttf'],
  ['Ded Lead', 400, ['EFT_Pnina.ttf', 'frank.otf'], 'FrankRuhlLibre.ttf'],
  ['Ded Verse', 400, ['stamashkenazyregular.ttf'], 'StamAshkenazCLM.ttf'],
];

(async () => {
  const src = process.argv[2] || path.join(__dirname, 'pages', 'hakdasha-yosef.json');
  const outDir = process.argv[3] || path.join(__dirname, 'out', 'pages');
  fs.mkdirSync(outDir, { recursive: true });
  const d = JSON.parse(fs.readFileSync(src, 'utf8')), c = d.classic;
  const css = FACES.map(([fam, w, files, fb, range]) => {
    let f = null;
    for (const n of files) for (const dir of DIRS) if (!f && fs.existsSync(path.join(dir, n))) f = path.join(dir, n);
    console.log(`${fam} ${w}: ${f ? path.basename(f) : 'fallback ' + fb}`);
    return `@font-face{font-family:"${fam}";font-weight:${w};${range ? 'unicode-range:' + range + ';' : ''}src:url("${encodeURI('file://' + (f || path.join(__dirname, 'assets', 'fonts', fb)))}");}`;
  }).join('\n');
  const ink = '#1a1a1a', soft = '#4a4a4a', rule = '#8f9296';
  const esc = (x) => x.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const lines = (a) => a.map(esc).join('<br>');
  const sep = '<img src="assets/cover/fleuron-sep.png">';

  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@page { size: ${T.w}mm ${T.h}mm; margin: 0; }
${css}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; }
body { font-kerning: normal; text-rendering: geometricPrecision; }
.page { position: relative; width: ${T.w}mm; height: ${T.h}mm; overflow: hidden; direction: rtl; color: ${ink}; background: #fff; }
.frame { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
.col { position: absolute; left: ${T.x0}mm; width: ${T.x1 - T.x0}mm; top: ${T.top}mm; height: ${T.bottom - T.top}mm; display: flex; flex-direction: column; align-items: center; text-align: center; }
.titlerow { display: flex; align-items: center; justify-content: center; width: 100%; flex: none; }
.titlerow .fl { width: 5.4mm; height: 21mm; position: relative; flex: none; }
.titlerow .fl img { position: absolute; left: 50%; top: 50%; width: 21mm; height: auto; transform: translate(-50%, -50%) rotate(90deg); }
.titlerow .mir { transform: scaleX(-1); }
.band { flex: 1 1 auto; background: linear-gradient(to bottom, #ececed, #e2e2e3); border-top: 0.3mm solid ${rule}; border-bottom: 0.3mm solid ${rule}; padding: 1.4mm 5mm 1.2mm; margin: 0 0.6mm; }
.t1 { font-family: "Ded Lead"; font-size: 13pt; line-height: 1.2; color: ${soft}; }
.book { font-family: "Ded Title"; font-size: 34pt; line-height: 1.15; }
.sp { flex: 1 1 0; }
.t2 { font-family: "Ded Lead"; font-size: 15pt; line-height: 1.55; }
.honor { font-family: "Ded Lead"; font-size: 14pt; line-height: 1.5; color: ${soft}; }
.nf { position: relative; width: 142mm; aspect-ratio: 3304 / 995; margin-top: 1.6mm; display: flex; align-items: center; justify-content: center; }
.nf > img { position: absolute; inset: 0; width: 100%; height: 100%; }
.name { position: relative; font-family: "Ded Name"; font-size: 34pt; line-height: 1; white-space: nowrap; margin-top: 0.8mm; }
.hy { font-family: "Ded Lead"; font-size: 15pt; margin-top: 1.4mm; }
.div { width: 104mm; height: auto; display: block; }
.bless { font-family: "Ded Text"; font-weight: 700; font-size: 16pt; line-height: 1.62; }
.verse { font-family: "Ded Verse"; font-size: 25pt; line-height: 1.3; margin-top: 2.2mm; }
.endo { width: 50mm; height: auto; display: block; }
</style></head><body><div class="page" id="pg"><img class="frame" src="assets/haskamot/frame-silver.png">
<div class="col" id="col">
<div class="titlerow"><div class="fl">${sep}</div><div class="band"><div class="t1">${lines(c.top)}</div><div class="book">${esc(c.book)}</div></div><div class="fl mir">${sep}</div></div>
<div class="sp" style="flex-grow:1"></div>
<div class="t2">${lines(c.sub)}</div>
<div class="sp" style="flex-grow:0.8"></div>
<div class="honor">${lines(c.honor)}</div>
<div class="nf"><img src="assets/ornaments/frame.png"><div class="name" id="name">${esc(c.name)}</div></div>
<div class="hy">${esc(c.hy)}</div>
<div class="sp" style="flex-grow:1"></div>
<img class="div" src="assets/ornaments/divider-long.png">
<div class="sp" style="flex-grow:1"></div>
<div class="bless">${lines(c.blessing)}</div>
<div class="verse">״${esc(c.verse.text)}״</div>
<div class="sp" style="flex-grow:1.1"></div>
<img class="endo" src="assets/ornaments/flourish-wide-2.png">
</div></div></body></html>`;
  fs.writeFileSync(path.join(__dirname, '_dedication.html'), html);

  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 4 });
  await p.goto('file://' + path.join(__dirname, '_dedication.html'));
  await p.evaluate(async () => { await Promise.all([...document.images].map((i) => i.decode().catch(() => {}))); await document.fonts.ready; });
  const fit = await p.evaluate((MMv) => {
    // the name: the largest size (up to 40 pt) at which it fits on one line inside the opening of the title frame of the booklet (74 % of its width)
    const name = document.getElementById('name'), col = document.getElementById('col'), nf = name.parentElement;
    let s = 40;
    for (; s > 16; s -= 0.25) { name.style.fontSize = s + 'pt'; if (name.getBoundingClientRect().width <= 0.74 * nf.clientWidth) break; }
    const free = [...col.querySelectorAll('.sp')].reduce((u, e) => u + e.getBoundingClientRect().height, 0);
    return { namePt: s, freeMm: +(free / MMv).toFixed(1) };
  }, MM);
  console.log(JSON.stringify(fit));
  if (fit.freeMm < 12) { console.error('the page is too full'); await browser.close(); process.exit(1); }
  await p.pdf({ path: path.join(outDir, d.id + '-classic.pdf'), width: `${T.w}mm`, height: `${T.h}mm`, printBackground: true, preferCSSPageSize: true });
  await p.locator('#pg').screenshot({ path: path.join(outDir, d.id + '-classic.png') });
  await browser.close();
})();
