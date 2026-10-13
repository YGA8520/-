#!/usr/bin/env node
/* A page of quotations (a title, cards "who said it / who he is / what he said", a closing line) in the style of the haskamot: one B5 page between the two silver side
 * rails of the frame of the cover, the title in the light-grey band with the two standing flourishes, the names in light-silver chips, the offices in graphite chips.
 *   node quotes_page_build.js pages/<name>.json [out_dir]    ->  out_dir/<id>.pdf, out_dir/<id>.png
 * The cards keep their order (right column first, then the middle, then the left); they are cut into three columns of the same height, and the text takes the largest
 * size at which everything fits. */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const MM = 96 / 25.4;
const T = { w: 176, h: 250, x0: 17, x1: 159, top: 5.5, bottom: 244.5, gap: 3.4, minGap: 5.7, sepW: 12 };       // page, the free area between the rails, gap between the columns, least distance between two cards, the small ornament between them included (mm)

(async () => {
  const src = process.argv[2] || path.join(__dirname, 'pages', 'chiuv-tefila.json');
  const outDir = process.argv[3] || path.join(__dirname, 'out', 'pages');
  fs.mkdirSync(outDir, { recursive: true });
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
  const data = JSON.parse(fs.readFileSync(src, 'utf8'));
  const F = Object.assign({ body: 'FrankRuehl DP', display: 'Ashkenazy', toc: 'HadasaNew', author: 'Shofar' }, cfg.fonts);
  const css = (cfg.fontFaces || []).map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};${f.unicodeRange ? 'unicode-range:' + f.unicodeRange + ';' : ''}src:url("assets/fonts/${f.file}");}`).join('\n');
  const ink = '#1c1c1c', soft = '#4a4a4a', rule = '#8f9296';
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const rich = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\{tel:([^}]+)\}/g, '<bdi dir="ltr">$1</bdi>');
  const sep = '<img src="assets/cover/fleuron-sep.png">';
  const colW = (T.x1 - T.x0 - 2 * T.gap) / 3;

  const card = (c) => `<div class="card"><div class="hd"><div class="who">${rich(c.who)}</div><div class="role">${rich(c.role)}</div></div>` +
    c.paras.map((t) => `<div class="pc"><p class="q">${rich(t)}</p></div>`).join('') + (c.src ? `<p class="src">${rich(c.src)}</p>` : '') + '</div>';

  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@page { size: ${T.w}mm ${T.h}mm; margin: 0; }
${css}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; -webkit-print-color-adjust: exact; }
body { font-kerning: normal; text-rendering: geometricPrecision; }
.page { position: relative; width: ${T.w}mm; height: ${T.h}mm; overflow: hidden; direction: rtl; color: ${ink}; background: #fff; --q: 9pt; }
.frame { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
.col { position: absolute; left: ${T.x0}mm; width: ${T.x1 - T.x0}mm; top: ${T.top}mm; height: ${T.bottom - T.top}mm; display: flex; flex-direction: column; align-items: center; text-align: center; }
.titlerow { display: flex; align-items: center; justify-content: center; width: 100%; flex: none; }
.titlerow .fl { width: 5.4mm; height: 21mm; position: relative; flex: none; }
.titlerow .fl img { position: absolute; left: 50%; top: 50%; width: 21mm; height: auto; transform: translate(-50%, -50%) rotate(90deg); }
.titlerow .mir { transform: scaleX(-1); }
.band { flex: 1 1 auto; background: linear-gradient(to bottom, #ececed, #e2e2e3); border-top: 0.3mm solid ${rule}; border-bottom: 0.3mm solid ${rule}; padding: 1.8mm 5mm 1.6mm; margin: 0 0.6mm; }
.title { font-family: "${F.display}"; font-size: 22pt; line-height: 1.12; color: ${ink}; text-align: center; }
.title .tl { display: block; white-space: nowrap; }
.title .tl span { display: inline-block; }
.cols { flex: 1 1 0; width: 100%; margin: 3.4mm 0 3.2mm; display: flex; flex-direction: row; gap: ${T.gap}mm; min-height: 0; }
.foot { margin-top: auto; }
.cols .c { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; justify-content: space-between; }
.sep { flex: none; display: flex; justify-content: center; align-items: center; }
.sep img { width: ${T.sepW}mm; height: auto; display: block; }
#pool { position: absolute; left: 0; top: 0; width: ${colW}mm; visibility: hidden; }
.card { font-size: var(--q); }
.who, .role { text-wrap: balance; }
.q, .src { text-wrap: pretty; }
.who { font-family: "${F.toc}"; font-weight: 700; font-size: 0.98em; line-height: 1.2; padding: 0.9mm 1.4mm 0.8mm; color: #3a3d42; background: linear-gradient(to bottom, #ececed, #e0e0e1); border-top: 0.25mm solid ${rule}; border-bottom: 0.25mm solid ${rule}; }
.role { font-family: "${F.toc}"; font-size: 0.9em; line-height: 1.2; padding: 0.9mm 1.4mm; margin-top: 1mm; color: #f1f1f2; background: linear-gradient(to bottom, #4b4f55, #33363b); }
.pc { margin-top: 1.9mm; }
.pc + .pc { margin-top: 1.5mm; }
.card.cont > .pc:first-child { margin-top: 0; }
.q { font-family: "${F.body}"; font-size: 1em; line-height: 1.27; margin: 0; }
.q b { font-weight: 700; }
.src { font-family: "${F.body}"; font-size: 0.86em; margin: 0; color: ${soft}; line-height: 1.2; margin-top: 0.9mm; }
.foot { flex: none; width: 100%; padding: 1.7mm 3mm 1.5mm; color: #f1f1f2; background: linear-gradient(to bottom, #4b4f55, #33363b); border-top: 0.3mm solid ${rule}; border-bottom: 0.3mm solid ${rule}; font-family: "${F.toc}"; line-height: 1.35; }
.foot .l1 { font-size: 9.2pt; }
.foot .l2 { font-size: 9.6pt; font-weight: 700; }
.foot .d { display: inline-block; width: 1.3mm; height: 1.3mm; background: #c9cacc; transform: rotate(45deg); margin: 0 2.4mm; vertical-align: 0.4mm; }
</style></head><body><div class="page" id="pg"><img class="frame" src="assets/haskamot/frame-silver.png">
<div class="col" id="col"><div class="titlerow"><div class="fl">${sep}</div><div class="band" id="band"><div class="title" id="title">${data.title.map((l) => `<span class="tl"><span>${esc(l)}</span></span>`).join('')}</div></div><div class="fl mir">${sep}</div></div>
<div class="cols" id="cols"></div>
<div class="foot"><div class="l1"><i class="d"></i>${rich(data.footer[0])}<i class="d"></i></div><div class="l2">${rich(data.footer[1])}</div></div></div>
<div id="pool">${data.cards.map(card).join('')}</div></div></body></html>`;
  fs.writeFileSync(path.join(__dirname, '_quotes.html'), html);

  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, '_quotes.html'));
  await p.evaluate(async () => { await Promise.all([...document.images].map((i) => i.decode().catch(() => {}))); });
  await p.evaluate(async (fams) => { await Promise.all(fams.flatMap((f) => [400, 700].map((w) => document.fonts.load(w + ' 16px "' + f + '"', 'אבג')))); await document.fonts.ready; }, [F.body, F.display, F.toc]);

  const fit = await p.evaluate(([MMv, minGap, sepHTML]) => {
    const pg = document.getElementById('pg'), pool = document.getElementById('pool'), cols = document.getElementById('cols'), band = document.getElementById('band'), title = document.getElementById('title');
    // the title: the largest size at which the longer line fits into the band
    let ts = 26;
    for (; ts > 12; ts -= 0.25) {
      title.style.fontSize = ts + 'pt';
      const w = Math.max(...[...title.querySelectorAll('.tl > span')].map((e) => e.getBoundingClientRect().width));
      if (w <= band.clientWidth - 2 * 5 * MMv + 0.5) break;
    }
    const cards = [...pool.children], avail = cols.getBoundingClientRect().height;

    // the cards are cut into three columns of the same height: a cut falls between two cards or - where a long quotation needs it - between two lines of a quotation
    // (at least two lines stay on each side); inside a column the cards spread out evenly, so that all three columns begin and end together
    const measure = () => {
      const atoms = [];
      cards.forEach((card, ci) => {
        atoms.push({ t: 'head', ci, h: card.querySelector('.hd').getBoundingClientRect().height, mt: 0 });
        card.querySelectorAll('.pc').forEach((pc, j) => {
          const p = pc.firstElementChild, lh = parseFloat(getComputedStyle(p).fontSize) * 1.27, n = Math.max(1, Math.round(p.getBoundingClientRect().height / lh)), mt = parseFloat(getComputedStyle(pc).marginTop);
          for (let l = 0; l < n; l++) atoms.push({ t: 'line', ci, j, l, n, h: lh, mt: l === 0 ? mt : 0 });
        });
        const src = card.querySelector('.src');
        if (src) atoms.push({ t: 'src', ci, h: src.getBoundingClientRect().height, mt: parseFloat(getComputedStyle(src).marginTop) });
      });
      return atoms;
    };
    const allowed = (at, k) => { const a = at[k - 1], b = at[k]; if (b.t === 'head') return true; if (b.t === 'src' || a.t === 'head') return false; return b.l === 0 || (b.l >= 2 && b.n - b.l >= 2); };
    const search = (at) => {
      const N = at.length, H = [0], M = [0], B = [0];
      at.forEach((x, k) => { H.push(H[k] + x.h); M.push(M[k] + x.mt); B.push(B[k] + (x.t === 'head' ? 1 : 0)); });
      const col = (s, e) => { const h = H[e] - H[s] + (M[e] - M[s + 1]), blocks = 1 + (B[e] - B[s + 1]); return { h, blocks, gap: blocks > 1 ? (avail - h) / (blocks - 1) : 1e9 }; };
      const cuts = []; for (let k = 1; k < N; k++) if (allowed(at, k)) cuts.push(k);
      let res = null;
      for (const c1 of cuts) for (const c2 of cuts) {
        if (c2 <= c1) continue;
        const cs = [col(0, c1), col(c1, c2), col(c2, N)];
        cs.forEach((c, i) => { c.i = i; });
        const lo = Math.min(...cs.map((c) => c.gap)), hi = Math.max(...cs.map((c) => c.gap));
        const cost = (hi - lo) + 0.35 * hi;
        if (lo / MMv >= minGap && (!res || cost < res.cost)) res = { hi, lo, cost, c: [c1, c2], pred: cs.map((c) => +(c.h / MMv).toFixed(1)) };
      }
      return res;
    };
    let pick = null;
    for (let q = 11.5; q >= 6.5; q -= 0.05) {
      pg.style.setProperty('--q', q + 'pt');
      const at = measure(), r = search(at);
      if (r && (!pick || r.cost < pick.cost - 0.15 * MMv)) pick = { q, at, ...r };
    }
    if (!pick) return { error: 'does not fit' };
    pg.style.setProperty('--q', pick.q + 'pt');
    const at = pick.at, bounds = [0, ...pick.c, at.length];
    // build the three columns; a quotation that is cut is shown twice, each time clipped to its own lines
    const piece = (s, e) => {
      const spec = {};
      for (let k = s; k < e; k++) { const x = at[k], d = spec[x.ci] || (spec[x.ci] = { head: false, src: false, paras: {} }); if (x.t === 'head') d.head = true; else if (x.t === 'src') d.src = true; else { const r = d.paras[x.j] || (d.paras[x.j] = [x.l, x.l]); r[1] = x.l + 1; } }
      return Object.entries(spec).map(([ci, d]) => {
        const src = cards[ci], div = document.createElement('div'); div.className = 'card' + (d.head ? '' : ' cont');
        if (d.head) div.appendChild(src.querySelector('.hd').cloneNode(true));
        src.querySelectorAll('.pc').forEach((pc, j) => {
          const r = d.paras[j]; if (!r) return;
          const w = pc.cloneNode(true), p = w.firstElementChild, lh = parseFloat(getComputedStyle(pc.firstElementChild).fontSize) * 1.27, n = Math.round(pc.firstElementChild.getBoundingClientRect().height / lh);
          if (r[0] > 0 || r[1] < n) { w.style.height = (r[1] - r[0]) * lh + 'px'; w.style.overflow = 'hidden'; p.style.marginTop = (-r[0] * lh) + 'px'; }
          div.appendChild(w);
        });
        if (d.src) div.appendChild(src.querySelector('.src').cloneNode(true));
        return div;
      });
    };
    const fitInfo = [];
    for (let c = 0; c < 3; c++) { const col = document.createElement('div'); col.className = 'c'; piece(bounds[c], bounds[c + 1]).forEach((d, i) => { if (i) { const sp = document.createElement('div'); sp.className = 'sep'; sp.innerHTML = sepHTML; col.appendChild(sp); } col.appendChild(d); }); cols.appendChild(col); }
    pool.remove();
    [...cols.children].forEach((col) => { const k = [...col.children].filter((e) => e.classList.contains('card')), h = k.reduce((u, e) => u + e.getBoundingClientRect().height, 0); fitInfo.push({ blocks: k.length, textMm: +(h / MMv).toFixed(1), gapMm: +(((avail - h) / Math.max(k.length - 1, 1)) / MMv).toFixed(1) }); });
    const split = [...new Set(at.slice(bounds[1] - 1, bounds[1] + 1).concat(at.slice(bounds[2] - 1, bounds[2] + 1)).filter((x) => x.t === 'line').map((x) => x.ci + 1))];
    return { titlePt: ts, quotePt: +pick.q.toFixed(2), availMm: +(avail / MMv).toFixed(1), columns: fitInfo, cardsCutAcrossColumns: split, predictedTextMm: pick.pred };
  }, [MM, T.minGap, sep]);
  console.log(JSON.stringify(fit));
  if (fit.error) { await browser.close(); process.exit(1); }
  const chk = await p.evaluate(() => { const pr = document.getElementById('col').getBoundingClientRect(); let m = 0, r = 0, l = 1e9; document.querySelectorAll('#col *').forEach((e) => { const b = e.getBoundingClientRect(); if (b.width && b.height && e.tagName !== 'IMG') { m = Math.max(m, b.bottom); r = Math.max(r, b.right); l = Math.min(l, b.left); } }); return { bottomOver: +((m - pr.bottom) / (96 / 25.4)).toFixed(2), sideOver: +(Math.max(r - pr.right, pr.left - l) / (96 / 25.4)).toFixed(2) }; });
  console.log('overflow (mm, <= 0 is fine):', JSON.stringify(chk));

  await p.pdf({ path: path.join(outDir, data.id + '.pdf'), width: `${T.w}mm`, height: `${T.h}mm`, printBackground: true, preferCSSPageSize: true });
  await p.locator('#pg').screenshot({ path: path.join(outDir, data.id + '.png') });
  await browser.close();
})();
