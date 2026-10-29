#!/usr/bin/env node
/* A dedication page (הקדשה) in the style of the haskamot and the page of quotations: one B5 page between the two silver side rails of the frame of the cover, the title
 * in the light-grey band with the two standing flourishes, the lead text, the name of the donor as the largest line of the page, the blessing in a light-silver card,
 * two verses, the logo of the organisation at the foot.
 *   node dedication_page_build.js pages/<name>.json [out_dir]    ->  out_dir/<id>.pdf, out_dir/<id>.png
 * The fonts of the booklet are used where they are installed (config.json); otherwise the free fonts in assets/fonts take their place (Stam Ashkenaz, Keter YG,
 * Frank Ruhl Libre, David Libre). The name takes the largest size at which it fits on one line; the free height is spread evenly between the blocks. */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const MM = 96 / 25.4;
const T = { w: 176, h: 250, x0: 17, x1: 159, top: 5.5, bottom: 244.5 };

(async () => {
  const src = process.argv[2] || path.join(__dirname, 'pages', 'hakdasha-yosef.json');
  const outDir = process.argv[3] || path.join(__dirname, 'out', 'pages');
  fs.mkdirSync(outDir, { recursive: true });
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
  const d = JSON.parse(fs.readFileSync(src, 'utf8'));
  const have = (f) => fs.existsSync(path.join(__dirname, 'assets', 'fonts', f.file));
  const css = (cfg.fontFaces || []).filter(have).map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};${f.unicodeRange ? 'unicode-range:' + f.unicodeRange + ';' : ''}src:url("assets/fonts/${f.file}");}`).join('\n') + `
@font-face{font-family:"Stam Free";src:url("assets/fonts/StamAshkenazCLM.ttf");}
@font-face{font-family:"Keter Free";font-weight:400;src:url("assets/fonts/KeterYG-Medium.ttf");}
@font-face{font-family:"Keter Free";font-weight:700;src:url("assets/fonts/KeterYG-Bold.ttf");}
@font-face{font-family:"Frank Free";src:url("assets/fonts/FrankRuhlLibre.ttf");font-weight:300 900;}
@font-face{font-family:"David Free";font-weight:400;src:url("assets/fonts/DavidLibre-Regular.ttf");}
@font-face{font-family:"David Free";font-weight:700;src:url("assets/fonts/DavidLibre-Bold.ttf");}`;
  const F = { display: `"Ashkenazy", "Stam Free"`, name: `"Ashkenazy", "Stam Free"`, head: `"HadasaNew", "Keter Free"`, body: `"FrankRuehl DP", "Frank Free"`, verse: `"FrankRuehl DP", "David Free"` };
  const ink = '#1c1c1c', soft = '#4a4a4a', rule = '#8f9296';
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const rich = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  const sep = '<img src="assets/cover/fleuron-sep.png">';

  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@page { size: ${T.w}mm ${T.h}mm; margin: 0; }
${css}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; }
body { font-kerning: normal; text-rendering: geometricPrecision; }
.page { position: relative; width: ${T.w}mm; height: ${T.h}mm; overflow: hidden; direction: rtl; color: ${ink}; background: #fff; }
.frame { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
.col { position: absolute; left: ${T.x0}mm; width: ${T.x1 - T.x0}mm; top: ${T.top}mm; height: ${T.bottom - T.top}mm; display: flex; flex-direction: column; align-items: center; justify-content: space-between; text-align: center; }
.bsd { position: absolute; top: 0; right: 1mm; font-family: ${F.head}; font-size: 8.5pt; color: ${soft}; }
.titlerow { display: flex; align-items: center; justify-content: center; width: 100%; margin-top: 4.5mm; }
.titlerow .fl { width: 5.4mm; height: 21mm; position: relative; flex: none; }
.titlerow .fl img { position: absolute; left: 50%; top: 50%; width: 21mm; height: auto; transform: translate(-50%, -50%) rotate(90deg); }
.titlerow .mir { transform: scaleX(-1); }
.band { flex: 1 1 auto; background: linear-gradient(to bottom, #ececed, #e2e2e3); border-top: 0.3mm solid ${rule}; border-bottom: 0.3mm solid ${rule}; padding: 1.6mm 5mm 1.2mm; margin: 0 0.6mm; }
.title { font-family: ${F.display}; font-size: 34pt; line-height: 1.1; letter-spacing: 0.08em; }
.lead { font-family: ${F.body}; font-size: 15pt; line-height: 1.45; }
.lead b { font-weight: 700; }
.lz { font-family: ${F.display}; font-size: 30pt; line-height: 1; color: #33363b; }
.orn img { display: block; width: 62mm; height: auto; opacity: 0.9; }
.honor { font-family: ${F.head}; font-size: 12.5pt; color: ${soft}; margin-bottom: 2.4mm; }
.name { font-family: ${F.name}; font-size: 40pt; line-height: 1.15; white-space: nowrap; color: #111; }
.namebox { display: flex; flex-direction: column; align-items: center; }
.rules { width: 100mm; height: 1.4mm; border-top: 0.3mm solid ${rule}; border-bottom: 0.3mm solid ${rule}; margin-top: 2.6mm; }
.card { width: 116mm; padding: 4.2mm 6mm 4mm; background: linear-gradient(to bottom, #f1f1f2, #e6e6e7); border-top: 0.35mm solid ${rule}; border-bottom: 0.35mm solid ${rule}; position: relative; }
.card p { font-family: ${F.body}; font-size: 12.5pt; line-height: 1.5; margin: 0; text-align: justify; text-align-last: center; text-wrap: pretty; }
.card p + p { margin-top: 1.6mm; }
.card b { font-weight: 700; }
.verses { display: flex; flex-direction: column; gap: 2.2mm; }
.v { font-family: ${F.verse}; font-size: 14pt; line-height: 1.3; }
.v .s { font-family: ${F.head}; font-size: 9pt; color: ${soft}; margin-right: 1.5mm; }
.foot { display: flex; flex-direction: column; align-items: center; margin-bottom: 3mm; }
.foot img { width: 21mm; height: auto; display: block; margin-top: 2mm; opacity: 0.95; }
.sign { font-family: ${F.head}; font-size: 11pt; line-height: 1.4; color: #33363b; }
.sign .s1 { font-size: 10pt; color: ${soft}; }
</style></head><body><div class="page" id="pg"><img class="frame" src="assets/haskamot/frame-silver.png">
<div class="col" id="col">
<div class="bsd">${esc(d.bsd)}</div>
<div class="titlerow"><div class="fl">${sep}</div><div class="band"><div class="title">${esc(d.title)}</div></div><div class="fl mir">${sep}</div></div>
<div class="lead">${d.lead.map(rich).join('<br>')}</div>
<div class="lz">${esc(d.lezchut)}</div>
<div class="namebox"><div class="honor">${esc(d.honor)}</div><div class="name" id="name">${esc(d.name)}</div><div class="rules"></div></div>
<div class="card">${d.blessing.map((t) => `<p>${rich(t)}</p>`).join('')}</div>
<div class="orn"><img src="assets/ornaments/divider-fleuron.png"></div>
<div class="verses">${d.verses.map((v) => `<div class="v">״${esc(v.text)}״<span class="s">(${esc(v.src)})</span></div>`).join('')}</div>
<div class="foot"><div class="sign"><div class="s1">${esc(d.sign[0])}</div><div>${esc(d.sign[1])}</div></div><img src="assets/cover/logo-grey.png"></div>
</div></div></body></html>`;
  fs.writeFileSync(path.join(__dirname, '_dedication.html'), html);

  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 4 });
  await p.goto('file://' + path.join(__dirname, '_dedication.html'));
  await p.evaluate(async () => { await Promise.all([...document.images].map((i) => i.decode().catch(() => {}))); await document.fonts.ready; });
  const fit = await p.evaluate((MMv) => {
    // the name: the largest size (up to 40 pt) at which it fits on one line with 6 mm on each side
    const name = document.getElementById('name'), col = document.getElementById('col');
    let s = 40;
    for (; s > 16; s -= 0.25) { name.style.fontSize = s + 'pt'; if (name.getBoundingClientRect().width <= col.clientWidth - 12 * MMv) break; }
    const kids = [...col.children].filter((e) => !e.classList.contains('bsd')), used = kids.reduce((u, e) => u + e.getBoundingClientRect().height, 0);
    const fonts = [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family.replace(/"/g, ''));
    return { namePt: s, freeMm: +((col.clientHeight - used) / MMv).toFixed(1), fonts: [...new Set(fonts)] };
  }, MM);
  console.log(JSON.stringify(fit));
  if (fit.freeMm < 10) { console.error('the page is too full'); await browser.close(); process.exit(1); }
  await p.pdf({ path: path.join(outDir, d.id + '.pdf'), width: `${T.w}mm`, height: `${T.h}mm`, printBackground: true, preferCSSPageSize: true });
  await p.locator('#pg').screenshot({ path: path.join(outDir, d.id + '.png') });
  await browser.close();
})();
