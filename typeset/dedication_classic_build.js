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
const A = { w: 142, r: 92, span: 0.76, top: 13, ow: 25, gap: 3.2, nest: 15 };      // the arc of the title: width of the svg, radius, half angle (rad), height of the apex of the baseline, width of a flourish, gap text-flourish, how far the lines below rise into the arc (mm)
A.cy = A.top + A.r; A.h = A.cy - A.r * Math.cos(A.span) + 6;
const DIRS = [path.join(__dirname, 'assets', 'fonts'), path.join(__dirname, '..', 'font-library', 'my-fonts', 'fonts'), process.env.FONT_DIR].filter(Boolean);
const NOQ = 'U+0000-05F2,U+05F5-10FFFF';
const FACES = [
  ['Ded Title', 400, ['EFT_Algebra OTS.ttf', 'ashkenazyregular.ttf'], 'StamAshkenazCLM.ttf'],
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
.arc { display: block; width: ${A.w}mm; height: ${A.h}mm; margin-top: 4mm; flex: none; overflow: visible; }
.arc text { font-family: "Ded Verse"; fill: ${ink}; }
.arc image { opacity: 0.8; }
.under { margin-top: -${A.nest}mm; display: flex; flex-direction: column; align-items: center; }
.t1 { font-family: "Ded Lead"; font-size: 14pt; line-height: 1.2; color: ${soft}; letter-spacing: 0.04em; }
.book { font-family: "Ded Title"; font-size: 38pt; line-height: 1.2; margin-top: 0.6mm; }
.sp { flex: 1 1 0; }
.t2 { font-family: "Ded Lead"; font-size: 15pt; line-height: 1.55; }
.honor { font-family: "Ded Lead"; font-size: 14pt; line-height: 1.5; color: ${soft}; }
.name { font-family: "Ded Name"; font-size: 44pt; line-height: 1.2; white-space: nowrap; margin-top: 2.4mm; }
.hy { font-family: "Ded Lead"; font-size: 15pt; margin-top: 1.4mm; }
.bless { font-family: "Ded Text"; font-weight: 700; font-size: 16pt; line-height: 1.62; }
.verse { font-family: "Ded Verse"; font-size: 25pt; line-height: 1.3; margin-top: 2.2mm; }
.endo { width: 50mm; height: auto; display: block; }
</style></head><body><div class="page" id="pg"><img class="frame" src="assets/haskamot/frame-silver.png">
<div class="col" id="col">
<svg class="arc" id="arc" viewBox="0 0 ${A.w} ${A.h}"><defs><path id="ap" d="M ${A.w / 2 - A.r * Math.sin(A.span)} ${A.cy - A.r * Math.cos(A.span)} A ${A.r} ${A.r} 0 0 1 ${A.w / 2 + A.r * Math.sin(A.span)} ${A.cy - A.r * Math.cos(A.span)}"/></defs>
<text id="title" direction="rtl" text-anchor="middle" font-size="12"><textPath href="#ap" startOffset="50%">${esc(c.title)}</textPath></text>
<image id="o1" href="assets/cover/fleuron-sep.png" width="${A.ow}" height="${A.ow * 168 / 648}"/><image id="o2" href="assets/cover/fleuron-sep.png" width="${A.ow}" height="${A.ow * 168 / 648}"/></svg>
<div class="under"><div class="t1">${lines(c.top)}</div>
<div class="book">${esc(c.book)}</div></div>
<div class="sp" style="flex-grow:0.5"></div>
<div class="t2">${lines(c.sub)}</div>
<div class="sp" style="flex-grow:0.8"></div>
<div class="honor">${lines(c.honor)}</div>
<div class="name" id="name">${esc(c.name)}</div>
<div class="hy">${esc(c.hy)}</div>
<div class="sp" style="flex-grow:1.4"></div>
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
  const fit = await p.evaluate(([MMv, arcGeom]) => {
    // the title: the largest size (up to 30 pt) that fills at most 70 % of the opening of the title frame; the name: the largest size (up to 44 pt) that fits the column
    // the title on the arc: the largest size (up to 16 mm) whose length is at most 66 % of the arc; the two flourishes stand on the arc just beyond its ends,
    // turned along it (the one on the right mirrored)
    const title = document.getElementById('title'), name = document.getElementById('name'), col = document.getElementById('col'), A = arcGeom;
    const arcLen = 2 * A.r * A.span;
    let t = 16;
    for (; t > 6; t -= 0.1) { title.setAttribute('font-size', t); if (title.getComputedTextLength() <= 0.66 * arcLen) break; }
    const half = title.getComputedTextLength() / 2 / A.r, oh = A.ow * 168 / 648;
    [['o1', -1], ['o2', 1]].forEach(([id, side]) => {
      const a = side * (half + (A.gap + A.ow / 2) / A.r), x = A.w / 2 + A.r * Math.sin(a), y = A.cy - A.r * Math.cos(a) - 0.36 * t;
      const deg = a * 180 / Math.PI, im = document.getElementById(id);
      im.setAttribute('x', -A.ow / 2); im.setAttribute('y', -oh / 2);
      im.setAttribute('transform', `translate(${x} ${y}) rotate(${deg})${side > 0 ? ' scale(-1 1)' : ''}`);
    });
    let s = 44;
    for (; s > 16; s -= 0.25) { name.style.fontSize = s + 'pt'; if (name.getBoundingClientRect().width <= col.clientWidth - 16 * MMv) break; }
    const free = [...col.querySelectorAll('.sp')].reduce((u, e) => u + e.getBoundingClientRect().height, 0);
    return { titleMm: +t.toFixed(1), namePt: s, freeMm: +(free / MMv).toFixed(1) };
  }, [MM, A]);
  console.log(JSON.stringify(fit));
  if (fit.freeMm < 12) { console.error('the page is too full'); await browser.close(); process.exit(1); }
  await p.pdf({ path: path.join(outDir, d.id + '-classic.pdf'), width: `${T.w}mm`, height: `${T.h}mm`, printBackground: true, preferCSSPageSize: true });
  await p.locator('#pg').screenshot({ path: path.join(outDir, d.id + '-classic.png') });
  await browser.close();
})();
