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
const T = { w: 176, h: 250, frame: 13, gap: 1.3 };                              // page; distance of the outer rule from the edge, distance between the two rules (mm)
const DIRS = [path.join(__dirname, 'assets', 'fonts'), path.join(__dirname, '..', 'font-library', 'my-fonts', 'fonts'), process.env.FONT_DIR].filter(Boolean);
const NOQ = 'U+0000-05F2,U+05F5-10FFFF';
const FACES = [
  ['Ded Title', 400, ['EFT_Algebra OTS.ttf', 'ashkenazyregular.ttf'], 'StamAshkenazCLM.ttf'],
  ['Ded Name', 400, ['MANTDEC.TTF', 'ashkenazyregular.ttf'], 'StamAshkenazCLM.ttf'],
  ['Ded Text', 400, ['MANTM.TTF', 'frank.otf'], 'FrankRuhlLibre.ttf'],
  ['Ded Text', 700, ['MANTB.TTF', 'פרנק בולד.otf'], 'FrankRuhlLibre.ttf'],
  ['Ded Lead', 400, ['livornaregular.ttf', 'frank.otf'], 'FrankRuhlLibre.ttf'],
  ['Ded Body', 400, ['frank.otf'], 'FrankRuhlLibre.ttf', NOQ],
  ['Ded Body', 700, ['פרנק בולד.otf'], 'FrankRuhlLibre.ttf', NOQ],
  ['Ded Body', 400, ['-'], 'FrankRuhlLibre.ttf', 'U+05F3-05F4'],
  ['Ded Body', 700, ['-'], 'FrankRuhlLibre.ttf', 'U+05F3-05F4'],
  ['Ded Small', 400, ['hadasanewregular.ttf'], 'DavidLibre-Regular.ttf'],
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
  const ink = '#1a1a1a', soft = '#555', rule = '#2a2a2a';
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const lines = (a) => a.map(esc).join('<br>');
  const f = T.frame, g = T.gap;

  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@page { size: ${T.w}mm ${T.h}mm; margin: 0; }
${css}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; }
body { font-kerning: normal; text-rendering: geometricPrecision; }
.page { position: relative; width: ${T.w}mm; height: ${T.h}mm; overflow: hidden; direction: rtl; color: ${ink}; background: #fff; }
.r1 { position: absolute; inset: ${f}mm; border: 0.45mm solid ${rule}; }
.r2 { position: absolute; inset: ${f + g}mm; border: 0.15mm solid ${rule}; }
.cn { position: absolute; width: 17mm; height: 17mm; background: url("assets/ornaments/corner.png") center / contain no-repeat; opacity: 0.85; }
.cn.tr { top: ${f + g + 1.2}mm; right: ${f + g + 1.2}mm; }
.cn.tl { top: ${f + g + 1.2}mm; left: ${f + g + 1.2}mm; transform: scaleX(-1); }
.cn.br { bottom: ${f + g + 1.2}mm; right: ${f + g + 1.2}mm; transform: scaleY(-1); }
.cn.bl { bottom: ${f + g + 1.2}mm; left: ${f + g + 1.2}mm; transform: scale(-1, -1); }
.col { position: absolute; left: ${f + 18}mm; right: ${f + 18}mm; top: ${f + 13}mm; bottom: ${f + 11}mm; display: flex; flex-direction: column; align-items: center; text-align: center; }
.fl { width: 15mm; height: auto; display: block; opacity: 0.9; }
.fl.dn { transform: scaleY(-1); }
.sp { flex: 1 1 0; }
.t1 { font-family: "Ded Lead"; font-size: 13pt; letter-spacing: 0.06em; }
.book { font-family: "Ded Title"; font-size: 30pt; line-height: 1.2; margin: 0.6mm 0 1.6mm; }
.t2 { font-family: "Ded Lead"; font-size: 13pt; line-height: 1.6; }
.honor { font-family: "Ded Lead"; font-size: 12.5pt; line-height: 1.55; color: ${soft}; }
.name { font-family: "Ded Name"; font-size: 40pt; line-height: 1.2; white-space: nowrap; margin-top: 2.4mm; }
.hy { font-family: "Ded Text"; font-size: 14pt; margin-top: 0.8mm; }
.bar { width: 26mm; border-top: 0.2mm solid ${rule}; }
.bless { font-family: "Ded Text"; font-size: 13.5pt; line-height: 1.62; }
.verse { font-family: "Ded Text"; font-weight: 700; font-size: 15pt; margin-top: 1.6mm; }
.verse .s { font-weight: 400; font-size: 9.5pt; color: ${soft}; margin-right: 1.5mm; }
.foot { display: flex; flex-direction: column; align-items: center; gap: 1.8mm; }
.foot img { width: 15mm; height: auto; display: block; opacity: 0.9; }
.sign { font-family: "Ded Small"; font-size: 9pt; color: ${soft}; letter-spacing: 0.02em; }
</style></head><body><div class="page" id="pg">
<div class="r1"></div><div class="r2"></div><div class="cn tr"></div><div class="cn tl"></div><div class="cn br"></div><div class="cn bl"></div>
<div class="col" id="col">
<img class="fl" src="assets/ornaments/fleuron-small.png">
<div class="sp" style="flex-grow:1.1"></div>
<div class="t1">${lines(c.top)}</div>
<div class="book">${esc(c.book)}</div>
<div class="t2">${lines(c.sub)}</div>
<div class="sp" style="flex-grow:0.9"></div>
<div class="honor">${lines(c.honor)}</div>
<div class="name" id="name">${esc(c.name)}</div>
<div class="hy">${esc(c.hy)}</div>
<div class="sp" style="flex-grow:1"></div>
<div class="bar"></div>
<div class="sp" style="flex-grow:1"></div>
<div class="bless">${lines(c.blessing)}</div>
<div class="verse">״${esc(c.verse.text)}״<span class="s">(${esc(c.verse.src)})</span></div>
<div class="sp" style="flex-grow:1.2"></div>
<img class="fl dn" src="assets/ornaments/fleuron-small.png">
<div class="sp" style="flex-grow:0.5"></div>
<div class="foot"><img src="assets/cover/logo-grey.png"><div class="sign">${esc(c.sign)}</div></div>
</div></div></body></html>`;
  fs.writeFileSync(path.join(__dirname, '_dedication.html'), html);

  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 4 });
  await p.goto('file://' + path.join(__dirname, '_dedication.html'));
  await p.evaluate(async () => { await Promise.all([...document.images].map((i) => i.decode().catch(() => {}))); await document.fonts.ready; });
  const fit = await p.evaluate((MMv) => {
    // the name: the largest size (up to 40 pt) at which it fits on one line
    const name = document.getElementById('name'), col = document.getElementById('col');
    let s = 40;
    for (; s > 16; s -= 0.25) { name.style.fontSize = s + 'pt'; if (name.scrollWidth <= col.clientWidth) break; }
    const free = [...col.querySelectorAll('.sp')].reduce((u, e) => u + e.getBoundingClientRect().height, 0);
    return { namePt: s, freeMm: +(free / MMv).toFixed(1) };
  }, MM);
  console.log(JSON.stringify(fit));
  if (fit.freeMm < 12) { console.error('the page is too full'); await browser.close(); process.exit(1); }
  await p.pdf({ path: path.join(outDir, d.id + '-classic.pdf'), width: `${T.w}mm`, height: `${T.h}mm`, printBackground: true, preferCSSPageSize: true });
  await p.locator('#pg').screenshot({ path: path.join(outDir, d.id + '-classic.png') });
  await browser.close();
})();
