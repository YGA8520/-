#!/usr/bin/env node
/* The dedication page, gold version: a page that stands out among the silver pages of the booklet but belongs to it - the gold frame of the cover (the back cover
 * background `assets/cover/back-bg.jpg`, soft palette), the navy of the logo, gold ornaments re-coloured from the ornaments of the booklet
 * (`make_dedication_ornaments.py`). The name of the donor sits in a navy medallion with a double gold rim and gold corner fleurons.
 *   node dedication_gold_build.js pages/<name>.json [out_dir]    ->  out_dir/<id>-gold.pdf, out_dir/<id>-gold.png, out_dir/<id>-gold-grey.png
 * Fonts are looked up in assets/fonts, in ../font-library/my-fonts/fonts and in $FONT_DIR: Ashkenazy (title), Keren (לזכות, the signature), EFT Frankfurt Decor
 * (the name), FrankRuehl DP (the text), HadasaNew (small lines). A missing font falls back to the free fonts in assets/fonts. */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const MM = 96 / 25.4;
const T = { w: 176, h: 250, x0: 27, x1: 149, top: 26, bottom: 225 };          // page; the parchment inside the gold frame (mm)
const DIRS = [path.join(__dirname, 'assets', 'fonts'), path.join(__dirname, '..', 'font-library', 'my-fonts', 'fonts'), process.env.FONT_DIR].filter(Boolean);
const NOQ = 'U+0000-05F2,U+05F5-10FFFF';                                       // FrankRuehl DP draws ׳ ״ empty: they come from Frank Ruhl Libre
const FACES = [
  ['Ded Title', 400, ['ashkenazyregular.ttf'], 'StamAshkenazCLM.ttf'],
  ['Ded Keren', 400, ['KERENM.TTF'], 'KeterYG-Medium.ttf'],
  ['Ded Keren', 700, ['KERENB.TTF'], 'KeterYG-Bold.ttf'],
  ['Ded Name', 400, ['EFT_Frankfurt Decor.ttf'], 'KeterYG-Bold.ttf'],
  ['Ded Body', 400, ['frank.otf'], 'FrankRuhlLibre.ttf', NOQ],
  ['Ded Body', 700, ['פרנק בולד.otf'], 'FrankRuhlLibre.ttf', NOQ],
  ['Ded Body', 400, ['-'], 'FrankRuhlLibre.ttf', 'U+05F3-05F4'],
  ['Ded Body', 700, ['-'], 'FrankRuhlLibre.ttf', 'U+05F3-05F4'],
  ['Ded Small', 400, ['hadasanewregular.ttf'], 'DavidLibre-Regular.ttf'],
  ['Ded Small', 700, ['hadasanewbold.ttf'], 'DavidLibre-Bold.ttf'],
];

(async () => {
  const src = process.argv[2] || path.join(__dirname, 'pages', 'hakdasha-yosef.json');
  const outDir = process.argv[3] || path.join(__dirname, 'out', 'pages');
  fs.mkdirSync(outDir, { recursive: true });
  const d = JSON.parse(fs.readFileSync(src, 'utf8'));
  const used = [];
  const css = FACES.map(([fam, w, files, fb, range]) => {
    let f = null;
    for (const n of files) for (const dir of DIRS) if (!f && fs.existsSync(path.join(dir, n))) f = path.join(dir, n);
    used.push(`${fam} ${w}: ${f ? path.basename(f) : 'fallback ' + fb}`);
    return `@font-face{font-family:"${fam}";font-weight:${w};${range ? 'unicode-range:' + range + ';' : ''}src:url("${encodeURI('file://' + (f || path.join(__dirname, 'assets', 'fonts', fb)))}");}`;
  }).join('\n');
  console.log(used.join(' | '));

  const navy = '#1d2a4a', navyDeep = '#111a31', gold = '#a8823a', goldDark = '#6f4f1c', champ = '#ead7a4';
  const goldText = `background: linear-gradient(to bottom, #f6e7b8 0%, #d8b464 38%, #b38a3c 55%, #e9cf8a 78%, #c9a050 100%); -webkit-background-clip: text; background-clip: text; color: transparent;`;
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const rich = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  const A = (n) => `assets/dedication/${n}-gold.png`;

  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@page { size: ${T.w}mm ${T.h}mm; margin: 0; }
${css}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-kerning: normal; text-rendering: geometricPrecision; }
.page { position: relative; width: ${T.w}mm; height: ${T.h}mm; overflow: hidden; direction: rtl; color: ${navy}; background: #fbf8f1 url("assets/cover/back-bg.jpg") center / 100% 100% no-repeat; }
.col { position: absolute; left: ${T.x0}mm; width: ${T.x1 - T.x0}mm; top: ${T.top}mm; height: ${T.bottom - T.top}mm; display: flex; flex-direction: column; align-items: center; justify-content: space-between; text-align: center; }
.bsd { position: absolute; top: ${T.top - 4}mm; right: ${T.w - T.x1 + 1}mm; font-family: "Ded Small"; font-size: 8.5pt; color: ${goldDark}; }
.head { display: flex; flex-direction: column; align-items: center; }
.title { font-family: "Ded Title"; font-size: 38pt; line-height: 1; letter-spacing: 0.06em; color: ${navy}; }
.head img { width: 52mm; height: auto; display: block; margin-top: 0.8mm; }
.lead { font-family: "Ded Body"; font-size: 13pt; line-height: 1.38; color: ${navy}; }
.lead b { font-weight: 700; }
.medal { position: relative; width: 116mm; padding: 5.5mm 6mm 5.2mm; border-radius: 3mm; background: radial-gradient(ellipse at 50% 35%, #2b3c66 0%, ${navy} 55%, ${navyDeep} 100%);
  border: 0.7mm solid ${gold}; box-shadow: 0 0 0 0.9mm #f7f1e2, 0 0 0 1.25mm ${goldDark}, 0 1.2mm 3mm rgba(60, 40, 10, 0.35); }
.medal::before { content: ""; position: absolute; inset: 1.6mm; border: 0.25mm solid rgba(234, 215, 164, 0.75); border-radius: 2mm; pointer-events: none; }
.medal .cn { position: absolute; width: 13mm; height: auto; }
.medal .tr { top: 2.2mm; right: 2.2mm; }
.medal .tl { top: 2.2mm; left: 2.2mm; transform: scaleX(-1); }
.medal .br { bottom: 2.2mm; right: 2.2mm; transform: scaleY(-1); }
.medal .bl { bottom: 2.2mm; left: 2.2mm; transform: scale(-1, -1); }
.lz { font-family: "Ded Keren"; font-weight: 700; font-size: 25pt; line-height: 1.05; ${goldText} }
.honor { font-family: "Ded Small"; font-size: 11pt; color: ${champ}; margin-top: 1.6mm; letter-spacing: 0.01em; }
.name { font-family: "Ded Name"; font-size: 40pt; line-height: 1.18; white-space: nowrap; margin-top: 0.6mm; ${goldText} filter: drop-shadow(0 0.25mm 0.2mm rgba(0, 0, 0, 0.45)); }
.medal .sc { width: 62mm; height: auto; display: block; margin: 1.6mm auto 0; }
.bless { width: 112mm; }
.bless p { font-family: "Ded Body"; font-size: 11.6pt; line-height: 1.45; margin: 0; text-align: justify; text-align-last: center; text-wrap: pretty; color: ${navy}; }
.bless p + p { margin-top: 1.3mm; }
.bless b { font-weight: 700; color: ${goldDark}; }
.orn { width: 56mm; height: auto; display: block; }
.verses { display: flex; flex-direction: column; gap: 1.6mm; }
.v { font-family: "Ded Body"; font-size: 13pt; line-height: 1.3; color: ${navy}; }
.v .s { font-family: "Ded Small"; font-size: 8.5pt; color: ${goldDark}; margin-right: 1.4mm; }
.foot { display: flex; align-items: center; justify-content: center; gap: 5mm; }
.foot img { width: 19mm; height: auto; display: block; }
.sign { font-family: "Ded Small"; font-size: 10pt; line-height: 1.38; color: ${navy}; text-align: right; }
.sign .s1 { color: ${goldDark}; }
.sign .s2 { font-family: "Ded Keren"; font-weight: 700; font-size: 12pt; }
</style></head><body><div class="page" id="pg">
<div class="bsd">${esc(d.bsd)}</div>
<div class="col" id="col">
<div class="head"><div class="title">${esc(d.title)}</div><img src="${A('line-scroll')}"></div>
<div class="lead">${d.lead.map(rich).join('<br>')}</div>
<div class="medal"><img class="cn tr" src="${A('fleuron-corner')}"><img class="cn tl" src="${A('fleuron-corner')}"><img class="cn br" src="${A('fleuron-corner')}"><img class="cn bl" src="${A('fleuron-corner')}">
<div class="lz">${esc(d.lezchut)}</div><div class="honor">${esc(d.honor)}</div>${(d.nameLines || [d.name]).map((l) => `<div class="name"><span class="nm">${esc(l)}</span></div>`).join('')}</div>
<div class="bless">${d.blessing.map((t) => `<p>${rich(t)}</p>`).join('')}</div>
<img class="orn" src="${A('divider-fleuron')}">
<div class="verses">${d.verses.map((v) => `<div class="v">״${esc(v.text)}״<span class="s">(${esc(v.src)})</span></div>`).join('')}</div>
<div class="foot"><div class="sign"><div class="s1">${esc(d.sign[0])}</div><div class="s2">${esc(d.sign[1])}</div></div><img src="assets/cover/logo.png"></div>
</div></div></body></html>`;
  fs.writeFileSync(path.join(__dirname, '_dedication.html'), html);

  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 4 });
  await p.goto('file://' + path.join(__dirname, '_dedication.html'));
  await p.evaluate(async () => { await Promise.all([...document.images].map((i) => i.decode().catch(() => {}))); await document.fonts.ready; });
  const fit = await p.evaluate((MMv) => {
    // the name (one or two lines, `nameLines`): the largest size (up to 44 pt) at which the longer line fits inside the medallion
    const names = [...document.querySelectorAll('.nm')], col = document.getElementById('col'), box = document.querySelector('.medal');
    let s = 44;
    for (; s > 16; s -= 0.25) { names.forEach((n) => { n.parentElement.style.fontSize = s + 'pt'; }); if (Math.max(...names.map((n) => n.getBoundingClientRect().width)) <= box.clientWidth - 30 * MMv) break; }
    const kids = [...col.children], usedH = kids.reduce((u, e) => u + e.getBoundingClientRect().height, 0);
    return { namePt: s, freeMm: +((col.clientHeight - usedH) / MMv).toFixed(1) };
  }, MM);
  console.log(JSON.stringify(fit));
  if (fit.freeMm < 8) { console.error('the page is too full'); await browser.close(); process.exit(1); }
  await p.pdf({ path: path.join(outDir, d.id + '-gold.pdf'), width: `${T.w}mm`, height: `${T.h}mm`, printBackground: true, preferCSSPageSize: true });
  await p.locator('#pg').screenshot({ path: path.join(outDir, d.id + '-gold.png') });
  // how the page looks if the interior is printed in black only
  await p.addStyleTag({ content: 'html { filter: grayscale(1); }' });
  await p.locator('#pg').screenshot({ path: path.join(outDir, d.id + '-gold-grey.png') });
  await browser.close();
})();
