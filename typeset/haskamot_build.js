#!/usr/bin/env node
/* The haskamot (approbation pages): one B5 page per haskama - the facsimile of the original (handwriting, or the printed letter as it is) and, where the original is
 * handwritten, the typed text on the same page; between two silver side rails (the frame of the cover, stretched so that its top and bottom are outside the page).
 *   node haskamot_build.js [out_dir]      ->  out_dir/haskamot-silver.pdf, out_dir/haskama-<id>.png
 * Content: haskamot/haskamot.json;  frame: python make_haskama_frame.py.  Nothing here is part of any booklet until it is merged. */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const MM = 96 / 25.4;
const T = { w: 176, h: 250, x0: 17, x1: 159, top: 11, bottom: 240 };       // page and the free area between the rails (mm); the axis is the middle of the page

(async () => {
  const outDir = process.argv[2] || path.join(__dirname, 'out', 'haskamot');
  fs.mkdirSync(outDir, { recursive: true });
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, 'haskamot', 'haskamot.json'), 'utf8'));
  const F = Object.assign({ body: 'FrankRuehl DP', display: 'Ashkenazy', toc: 'HadasaNew', author: 'Shofar' }, cfg.fonts);
  const css = (cfg.fontFaces || []).map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};${f.unicodeRange ? 'unicode-range:' + f.unicodeRange + ';' : ''}src:url("assets/fonts/${f.file}");}`).join('\n');
  const ink = '#1c1c1c', soft = '#4a4a4a', rule = '#8f9296';
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const rich = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  const sep = '<img src="assets/cover/fleuron-sep.png">';

  const pageHTML = (h) => {
    let body = '';
    if (h.layout === 'original') {
      body = `<div class="fac plain" id="fac"><img src="${h.original}"></div>`;
    } else {
      body = `<div class="fac" id="fac"><img src="${h.facsimile}"></div>` +
        (h.caption ? `<div class="cap">${esc(h.caption)}</div>` : '') +
        (h.date_right ? `<div class="dateline">${esc(h.date_right)}</div>` : '') +
        `<div class="txt" id="txt">${h.paras.map((p) => `<p>${rich(p)}</p>`).join('')}</div>` +
        (h.closing ? `<div class="closing">${esc(h.closing)}</div>` : '') +
        `<div class="sigs">${h.signatures.map((s) => `<span class="${/מצטרף/.test(s) ? 'join' : 'sig'}">${esc(s)}</span>`).join('')}</div>`;
    }
    return `<div class="page" data-id="${h.id}"><img class="frame" src="assets/haskamot/frame-silver.png">` +
      `<div class="col" id="col"><div class="titlerow"><div class="fl mir">${sep}</div><div class="title">${esc(data.title)}</div><div class="fl">${sep}</div></div>` +
      `<div class="head">${esc(h.head)}</div>${h.sub ? `<div class="sub">${esc(h.sub)}</div>` : ''}<div class="rule"></div>${body}</div></div>`;
  };

  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@page { size: ${T.w}mm ${T.h}mm; margin: 0; }
${css}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; }
body { font-kerning: normal; text-rendering: geometricPrecision; }
.page { position: relative; width: ${T.w}mm; height: ${T.h}mm; overflow: hidden; page-break-after: always; break-after: page; direction: rtl; color: ${ink}; background: #fff; }
.page:last-child { page-break-after: auto; break-after: auto; }
.frame { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
.col { position: absolute; left: ${T.x0}mm; width: ${T.x1 - T.x0}mm; top: ${T.top}mm; height: ${T.bottom - T.top}mm; display: flex; flex-direction: column; align-items: center; text-align: center; }
.titlerow { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; width: 100%; column-gap: 5mm; margin-top: 1mm; }
.titlerow .fl { display: flex; }
.titlerow .fl:first-child { justify-content: flex-start; }
.titlerow .fl:last-child { justify-content: flex-end; }
.titlerow .fl img { width: 17mm; display: block; }
.titlerow .mir img { transform: scaleX(-1); }
.title { font-family: "${F.display}"; font-size: 26pt; line-height: 1.05; margin: 0; color: ${ink}; text-align: center; }
.head { font-family: "${F.toc}"; font-weight: 700; font-size: 12.5pt; margin-top: 2.2mm; line-height: 1.25; }
.sub { font-family: "${F.toc}"; font-size: 9.5pt; margin-top: 0.8mm; color: ${soft}; line-height: 1.3; }
.rule { width: 64mm; height: 0.25mm; background: ${rule}; margin: 2.2mm 0 2.6mm; opacity: .85; flex: none; }
.fac { margin: 0 auto 3mm; padding: 1.6mm; background: #fffefb; border: 0.25mm solid ${soft}; box-shadow: 0.9mm 1.1mm 2.4mm rgba(40,40,40,.26), inset 0 0 0 0.9mm #fffefb, inset 0 0 0 1.15mm ${rule}; flex: none; position: relative; }
.fac.plain { padding: 0; border: 0; background: #fff; box-shadow: 0.9mm 1.1mm 2.6mm rgba(40,40,40,.30); }
.fac img { display: block; height: 100%; width: 100%; object-fit: contain; mix-blend-mode: multiply; }
.cap { font-family: "${F.display}"; font-size: 16pt; margin: 0 0 1.6mm; flex: none; }
.dateline { align-self: stretch; text-align: right; font-family: "${F.body}"; font-size: 10pt; color: ${soft}; margin-bottom: 0.6mm; flex: none; }
.txt { font-family: "${F.body}"; width: 100%; line-height: 1.3; flex: none; text-align: justify; text-align-last: right; }
.txt p { margin: 0 0 1.6mm; }
.txt b { font-weight: 700; }
.closing { font-family: "${F.body}"; margin-top: 1mm; flex: none; }
.sigs { display: flex; flex-wrap: wrap; justify-content: center; align-items: baseline; column-gap: 6mm; row-gap: 0.8mm; margin-top: 2mm; flex: none; }
.sig { font-family: "${F.author}"; font-weight: 700; font-size: 12pt; }
.join { font-family: "${F.body}"; font-size: 10pt; color: ${soft}; }
</style></head><body><div id="pages">${data.pages.map(pageHTML).join('')}</div></body></html>`;
  fs.writeFileSync(path.join(__dirname, '_haskamot.html'), html);

  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, '_haskamot.html'));
  await p.evaluate(async () => { await Promise.all([...document.images].map((i) => i.decode().catch(() => {}))); });
  await p.evaluate(async (fams) => { await Promise.all(fams.flatMap((f) => [400, 700].map((w) => document.fonts.load(w + ' 16px "' + f + '"', 'אבג')))); await document.fonts.ready; }, [F.body, F.display, F.toc, F.author]);

  // fit: the typed text takes the largest size that leaves the facsimile at least `minFac` mm of height; the facsimile takes what is left
  const fit = await p.evaluate(([MMv, bottom, top, minFac, maxW]) => {
    const res = [];
    document.querySelectorAll('.page').forEach((pg) => {
      const col = pg.querySelector('#col'), txt = pg.querySelector('#txt'), fac = pg.querySelector('#fac');
      const avail = (bottom - top) * MMv;
      const used = () => { let u = 0; col.childNodes.forEach((n) => { if (n.nodeType === 1 && n !== fac) { const r = n.getBoundingClientRect(), cs = getComputedStyle(n); u += r.height + parseFloat(cs.marginTop) + parseFloat(cs.marginBottom); } }); return u; };
      const img = fac.querySelector('img'), ratio = img.naturalWidth / img.naturalHeight, pad = fac.classList.contains('plain') ? 0 : 3.2;
      let chosen = null;
      if (txt) {
        const sizes = [11.5, 11, 10.5, 10, 9.5, 9, 8.5];
        chosen = sizes[sizes.length - 1];
        for (const s of sizes) { txt.style.fontSize = s + 'pt'; if (avail - used() - (pad + 3) * MMv >= minFac * MMv) { chosen = s; break; } }
        txt.style.fontSize = chosen + 'pt';
      }
      let hmm = Math.max((avail - used() - (pad + 3) * MMv) / MMv, 30);
      let wmm = Math.min(hmm * ratio, maxW - pad);
      hmm = wmm / ratio;
      fac.style.width = (wmm + pad) + 'mm'; fac.style.height = (hmm + pad) + 'mm';
      res.push({ id: pg.dataset.id, size: chosen, facW: +wmm.toFixed(1), facH: +hmm.toFixed(1), used: +(used() / MMv).toFixed(1), avail: bottom - top });
    });
    return res;
  }, [MM, T.bottom, T.top, 84, T.x1 - T.x0]);
  console.log(JSON.stringify(fit));
  const over = await p.evaluate((b) => [...document.querySelectorAll('.page')].map((pg) => { const col = pg.querySelector('#col'); let m = 0; col.querySelectorAll('*').forEach((e) => { m = Math.max(m, e.getBoundingClientRect().bottom - pg.getBoundingClientRect().top); }); return { id: pg.dataset.id, bottomMm: +(m / (96 / 25.4)).toFixed(1), limit: b }; }), T.bottom);
  console.log(JSON.stringify(over));
  // centring check of the title
  const ctr = await p.evaluate(() => [...document.querySelectorAll('.page')].map((pg) => { const t = pg.querySelector('.title').getBoundingClientRect(), pr = pg.getBoundingClientRect(); return +(((t.left + t.right) / 2 - (pr.left + pr.right) / 2) / (96 / 25.4)).toFixed(2); }));
  console.log('title offset from the page axis (mm):', JSON.stringify(ctr));

  await p.pdf({ path: path.join(outDir, 'haskamot-silver.pdf'), width: `${T.w}mm`, height: `${T.h}mm`, printBackground: true, preferCSSPageSize: true });
  for (const h of data.pages) await p.locator(`.page[data-id="${h.id}"]`).screenshot({ path: path.join(outDir, `haskama-${h.id}.png`) });
  await browser.close();
})();
