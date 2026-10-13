#!/usr/bin/env node
/* The haskamot (approbations) pages: one B5 page per haskama - the facsimile of the handwriting (if there is one) and the typed text on the same page, in the frame of the cover.
 *   node haskamot_build.js [out_dir] [silver|soft]      ->  out_dir/haskamot.pdf, out_dir/haskama-<id>.png / .jpg
 * Content: haskamot/haskamot.json (text, facsimile, titles); backgrounds: python make_haskama_bg.py.  Nothing here is part of the booklet until it is merged. */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const MM = 96 / 25.4;
const T = { w: 176, h: 250, axis: 88, x0: 27, x1: 149, top: 20, bottom: 225 };     // page, centre axis and the quiet interior of the frame (mm)

(async () => {
  const outDir = process.argv[2] || path.join(__dirname, 'out', 'haskamot');
  const style = process.argv[3] || 'silver';
  fs.mkdirSync(outDir, { recursive: true });
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, 'haskamot', 'haskamot.json'), 'utf8'));
  const F = Object.assign({ body: 'FrankRuehl DP', display: 'Ashkenazy', toc: 'HadasaNew', author: 'Shofar' }, cfg.fonts);
  const css = (cfg.fontFaces || []).map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};${f.unicodeRange ? 'unicode-range:' + f.unicodeRange + ';' : ''}src:url("assets/fonts/${f.file}");}`).join('\n');
  const ink = style === 'silver' ? '#1c1c1c' : '#392c20', soft = style === 'silver' ? '#4a4a4a' : '#6f5c45', rule = style === 'silver' ? '#8f9296' : '#a98f5c';
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const rich = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\[\.\.\.\]/g, '<span class="gap">[...]</span>').replace(/\[\?\]/g, '<span class="gap">[?]</span>');

  const pageHTML = (h) => {
    const sep = (w) => `<img src="assets/cover/fleuron-sep.png" style="width:${w}mm;display:block;margin:0 auto">`;
    let body;
    if (h.layout === 'letter') {
      body = `<div class="row"><span>${esc(h.date_right)}</span><span>${esc(h.date_left)}</span></div>` +
        `<div class="cap">${esc(h.caption)}</div>` +
        `<div class="txt justify" id="txt">${h.paras.map((p) => `<p>${rich(p)}</p>`).join('')}</div>` +
        `<div class="closing">${esc(h.closing)}</div>` +
        (h.signature ? `<img class="sigimg" src="${h.signature}">` : '') + `<div class="signed">${esc(h.signed)}</div>`;
    } else {
      const lines = h.lines ? `<div class="txt lines" id="txt">${h.date_right ? `<div class="dateline">${esc(h.date_right)}</div>` : ''}${h.lines.map((l) => `<div>${rich(l)}</div>`).join('')}${h.closing ? `<div class="closing2">${esc(h.closing)}</div>` : ''}</div>`
        : `<div class="txt justify" id="txt">${h.paras.map((p) => `<p>${rich(p)}</p>`).join('')}</div>`;
      body = `<div class="fac" id="fac"><img src="${h.facsimile}"></div>` + lines + `<div class="signed2">${esc(h.signed)}</div>` + (h.draft ? `<div class="draftnote">טיוטת תמלול של כתב היד · מילים שלא ניתן היה לקרוא מסומנות בסוגריים מרובעים</div>` : '');
    }
    return `<div class="page" data-id="${h.id}"><img class="bg" src="assets/haskamot/bg-${style}.jpg">` +
      `<div class="col" id="col"><div class="titlerow">${sep(15)}<div class="title">${esc(data.title)}</div><span class="mir">${sep(15)}</span></div>` +
      `<div class="head">${esc(h.head)}</div><div class="sub">${esc(h.sub)}</div>` +
      `<div class="rule"></div>${body}</div>` +
      `</div>`;
  };

  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@page { size: ${T.w}mm ${T.h}mm; margin: 0; }
${css}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; }
body { font-kerning: normal; text-rendering: geometricPrecision; }
.page { position: relative; width: ${T.w}mm; height: ${T.h}mm; overflow: hidden; page-break-after: always; break-after: page; direction: rtl; color: ${ink}; }
.page:last-child { page-break-after: auto; break-after: auto; }
.bg { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
.col { position: absolute; left: ${T.x0}mm; width: ${T.x1 - T.x0}mm; top: ${T.top}mm; height: ${T.bottom - T.top}mm; display: flex; flex-direction: column; align-items: center; text-align: center; }
.titlerow { display: flex; align-items: center; justify-content: center; gap: 5mm; width: 100%; margin-top: 1mm; }
.titlerow img { width: 15mm; flex: none; }
.mir { display: block; transform: scaleX(-1); }
.title { font-family: "${F.display}"; font-size: 25pt; line-height: 1.05; margin: 0; color: ${ink}; }
.head { font-family: "${F.toc}"; font-weight: 700; font-size: 12pt; margin-top: 2mm; line-height: 1.25; }
.sub { font-family: "${F.toc}"; font-size: 9.5pt; margin-top: 0.8mm; color: ${soft}; line-height: 1.3; }
.rule { width: 60mm; height: 0.25mm; background: ${rule}; margin: 2mm 0 2.4mm; opacity: .85; flex: none; }
.fac { margin: 0 auto 3.2mm; position: relative; padding: 1.6mm; background: #fffefb; border: 0.25mm solid ${soft}; box-shadow: 0.9mm 1.1mm 2.4mm rgba(40,40,40,.28), inset 0 0 0 0.9mm #fffefb, inset 0 0 0 1.15mm ${rule}; flex: none; }
.fac img { display: block; height: 100%; width: 100%; object-fit: contain; mix-blend-mode: multiply; }
.txt { font-family: "${F.body}"; width: 100%; line-height: 1.3; flex: none; }
.txt.justify { text-align: justify; text-align-last: right; }
.txt.justify p { margin: 0 0 1.8mm; text-indent: 0; }
.txt.lines { text-align: center; }
.txt.lines .dateline { text-align: right; font-size: .92em; color: ${soft}; margin-bottom: 0.8mm; }
.txt b { font-weight: 700; }
.gap { color: #8a8a8a; }
.closing2 { margin-top: 1mm; }
.signed2 { font-family: "${F.author}"; font-weight: 700; font-size: 12pt; margin-top: 1.8mm; flex: none; }
.row { display: flex; justify-content: space-between; width: 100%; font-family: "${F.toc}"; font-size: 10.5pt; color: ${soft}; margin-bottom: 2mm; }
.cap { font-family: "${F.display}"; font-size: 17pt; margin: 1.5mm 0 3.2mm; }
.closing { font-family: "${F.body}"; font-size: 12pt; margin-top: 3.4mm; }
.sigimg { width: 40mm; margin: 2.2mm 0 0; display: block; }
.signed { font-family: "${F.author}"; font-weight: 700; font-size: 13pt; margin-top: 0.8mm; }
.draftnote { font-family: "${F.toc}"; font-size: 8pt; color: #7a7a7a; margin-top: 1.4mm; flex: none; }
.draftmark { position: absolute; left: ${T.x0}mm; width: ${T.x1 - T.x0}mm; bottom: 12.5mm; text-align: center; font-family: "${F.toc}"; font-size: 8pt; color: #7a7a7a; }
</style></head><body><div id="pages">${data.pages.map(pageHTML).join('')}</div></body></html>`;
  fs.writeFileSync(path.join(__dirname, '_haskamot.html'), html);

  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, '_haskamot.html'));
  await p.evaluate(async () => { await Promise.all([...document.images].map((i) => i.decode().catch(() => {}))); });
  await p.evaluate(async (fams) => { await Promise.all(fams.flatMap((f) => [400, 700].map((w) => document.fonts.load(w + ' 16px "' + f + '"', 'אבג')))); await document.fonts.ready; }, [F.body, F.display, F.toc, F.author]);

  // fit: the typed text takes the largest size that leaves the facsimile at least `minFac` mm of height; the facsimile takes what is left
  const fit = await p.evaluate(([MMv, bottom, top, minFac, maxFac]) => {
    const res = [];
    document.querySelectorAll('.page').forEach((pg) => {
      const col = pg.querySelector('#col'), txt = pg.querySelector('#txt'), fac = pg.querySelector('#fac');
      const colTop = col.getBoundingClientRect().top, avail = (bottom - top) * MMv;
      const used = () => { let u = 0; col.childNodes.forEach((n) => { if (n.nodeType === 1 && n !== fac) { const r = n.getBoundingClientRect(), cs = getComputedStyle(n); u += r.height + parseFloat(cs.marginTop) + parseFloat(cs.marginBottom); } }); return u; };
      if (!fac) { const sizes = [15, 14.5, 14, 13.5, 13, 12.5, 12, 11.5, 11]; for (const s of sizes) { txt.style.fontSize = s + 'pt'; txt.style.lineHeight = '1.42'; if (used() <= avail - 10 * MMv) break; } const left = avail - used(); const row = pg.querySelector('.row'); if (row) row.style.marginTop = Math.max(0, left * 0.32) / MMv + 'mm'; res.push({ id: pg.dataset.id, size: txt.style.fontSize, left: +(left / MMv).toFixed(1), fac: null }); return; }
      const img = fac.querySelector('img'), ratio = img.naturalWidth / img.naturalHeight;
      const sizes = [11, 10.5, 10, 9.5, 9, 8.5];
      let chosen = sizes[sizes.length - 1];
      for (const s of sizes) { txt.style.fontSize = s + 'pt'; if (avail - used() - 6.4 * MMv >= minFac * MMv) { chosen = s; break; } }
      txt.style.fontSize = chosen + 'pt';
      let hmm = Math.min(maxFac, (avail - used() - 6.4 * MMv) / MMv);
      hmm = Math.max(hmm, 30);
      const wmm = Math.min(hmm * ratio, 104);
      hmm = wmm / ratio;
      fac.style.width = (wmm + 3.2) + 'mm'; fac.style.height = (hmm + 3.2) + 'mm';
      res.push({ id: pg.dataset.id, size: chosen, facW: +wmm.toFixed(1), facH: +hmm.toFixed(1), used: +(used() / MMv).toFixed(1), avail: bottom - top });
    });
    return res;
  }, [MM, T.bottom, T.top, 74, 112]);
  console.log(JSON.stringify(fit));
  // overflow check: nothing may leave the quiet interior of the frame
  const over = await p.evaluate((b) => [...document.querySelectorAll('.page')].map((pg) => { const col = pg.querySelector('#col'); let m = 0; col.querySelectorAll('*').forEach((e) => { m = Math.max(m, e.getBoundingClientRect().bottom - pg.getBoundingClientRect().top); }); return { id: pg.dataset.id, bottomMm: +(m / (96 / 25.4)).toFixed(1), limit: b }; }), T.bottom);
  console.log(JSON.stringify(over));

  await p.pdf({ path: path.join(outDir, `haskamot-${style}.pdf`), width: `${T.w}mm`, height: `${T.h}mm`, printBackground: true, preferCSSPageSize: true });
  for (const h of data.pages) {
    const el = p.locator(`.page[data-id="${h.id}"]`);
    await el.screenshot({ path: path.join(outDir, `haskama-${h.id}-${style}.png`) });
  }
  await browser.close();
})();
