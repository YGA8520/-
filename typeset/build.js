#!/usr/bin/env node
/* usage: node build.js doc.json out.pdf [config.json]   -> also writes out.json with layout stats */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
(async () => {
  const [,, docPath, outPdf, cfgPath = path.join(__dirname, 'config.json')] = process.argv;
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const doc = JSON.parse(fs.readFileSync(docPath, 'utf8'));
  // ---- fonts: roles (body / lead / display) and the font files that provide them -> config.json "fonts" and "fontFaces"
  const F = cfg.fonts = Object.assign({ body: 'Frank Ruhl Libre', lead: 'David Libre', display: 'Frank Ruhl Libre' }, cfg.fonts || {});
  F.notes = F.notes || F.body; F.author = F.author || F.lead;
  const WD = (cfg.fontWeights || {}).display || 800;                 // weight of the display (title) role: 800 for a variable family, 400 for a single-weight calligraphic face
  const WL = (cfg.fontWeights || {}).lead || 700;
  cfg.titleFrame.weight = WD; cfg.dividerFrame.weight = WD; cfg.type.h2.weight = WD; cfg.fontWeights = { display: WD, lead: WL };      // roles: body, lead (first word / sub-headings), display (titles), notes (footnotes), author (author names)
  Object.assign(cfg.type.body, { family: F.body }); Object.assign(cfg.type.foot, { family: F.notes });
  Object.assign(cfg.type.h2, { family: F.display }); Object.assign(cfg.type.h3, { family: F.lead });
  Object.assign(cfg.type.lead, { family: F.lead }); Object.assign(cfg.type.abstract, { family: F.lead });
  Object.assign(cfg.titleFrame, { family: F.display }); Object.assign(cfg.dividerFrame, { family: F.display });
  cfg.footnotes.titleFamily = F.lead;
  const faces = cfg.fontFaces || [];
  cfg.ornaments = {};
  const odir = path.join(__dirname, 'assets', 'ornaments');
  for (const f of fs.readdirSync(odir)) {
    if (!f.endsWith('.png')) continue;
    const buf = fs.readFileSync(path.join(odir, f));
    cfg.ornaments[f.replace(/\.png$/, '')] = { src: 'assets/ornaments/' + f, w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  }
  const cdir = path.join(odir, 'composed');
  if (fs.existsSync(cdir)) for (const f of fs.readdirSync(cdir)) {
    if (!f.endsWith('.png')) continue;
    const buf = fs.readFileSync(path.join(cdir, f));
    cfg.ornaments[f.replace(/\.png$/, '')] = { src: 'assets/ornaments/composed/' + f, w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  }
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', (m) => console.log('[page]', m.text()));
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto('file://' + path.join(__dirname, 'template.html'));
  await page.addStyleTag({ content: `:root{--f-body:"${F.body}";--f-lead:"${F.lead}";--f-display:"${F.display}";--f-notes:"${F.notes}";--f-author:"${F.author}";--w-notes:${cfg.type.foot.weight || 400};--w-display:${WD};--w-lead:${WL};}\n` +
    faces.map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};font-style:${f.style || 'normal'};${f.unicodeRange ? 'unicode-range:' + f.unicodeRange + ';' : ''}src:url("assets/fonts/${f.file}");}`).join('\n') });
  await page.addScriptTag({ path: path.join(__dirname, 'engine.js') });
  await page.evaluate(async (fontSpecs) => {
    await Promise.all(fontSpecs.map((f) => document.fonts.load(f, 'אבג')));
    await document.fonts.ready;
  }, [400, 700, 800].flatMap((w) => [F.body, F.lead, F.display, F.notes, F.author].map((fam) => `${w} 16px "${fam}"`)));
  const res = await page.evaluate(([c, d]) => window.typeset(c, d), [cfg, doc]);
  await page.evaluate(async () => {
    const urls = new Set([...document.body.innerHTML.matchAll(/url\(([^)]+)\)/g)].map((m) => m[1]));
    await Promise.all([...urls].map((u) => new Promise((r) => { const i = new Image(); i.onload = i.onerror = r; i.src = u; })));
    await Promise.all([...document.images].map((i) => i.decode().catch(() => {})));
  });
  const check = await page.evaluate(() => {
    const bad = [];
    document.querySelectorAll('.ln').forEach((el) => { if (el.scrollWidth > el.clientWidth + 1.5) bad.push(el.textContent.slice(0, 40) + ' ' + el.scrollWidth + '>' + el.clientWidth); });
    return bad;
  });
  // vertical overflow: no text line may end below the text area of its page (a column that did not fit would run off the page)
  const vover = await page.evaluate(() => {
    const bad = [];
    document.querySelectorAll('.page').forEach((pg, i) => {
      const H = pg.clientHeight;
      pg.querySelectorAll('.ln').forEach((el) => {
        const bottom = parseFloat(el.style.top) + parseFloat(el.style.height);
        if (bottom > H - 14) bad.push('pdf page ' + (i + 1) + ': ' + el.textContent.slice(0, 30));
      });
    });
    return bad;
  });
  console.log('vertical overflow: lines below the page text area:', vover.length);
  if (vover.length) console.log(vover.slice(0, 8));
  // hanging indent: line 2 must start exactly where the regular text of line 1 starts, and must never open a column
  const hang = await page.evaluate(() => {
    let ok = 0, off = [], orphan = 0, maxDev = 0;
    document.querySelectorAll('.hangln').forEach((el) => {
      const prev = el.previousElementSibling;
      if (!prev || !prev.classList.contains('leadln') || Math.abs(parseFloat(prev.style.left) - parseFloat(el.style.left)) > 0.5) { orphan++; return; }
      const mk = prev.querySelector('.le');
      if (!mk) return;
      const dev = mk.getBoundingClientRect().left - el.getBoundingClientRect().right;
      maxDev = Math.max(maxDev, Math.abs(dev));
      if (Math.abs(dev) > 0.6) off.push(prev.textContent.slice(0, 30) + ' // ' + el.textContent.slice(0, 20) + ' ' + dev.toFixed(2)); else ok++;
    });
    return { ok, off: off.slice(0, 8), nOff: off.length, orphan, maxDev: +maxDev.toFixed(2) };
  });
  console.log('hanging indent: aligned', hang.ok, ' misaligned', hang.nOff, ' column-top (unindented needed)', hang.orphan, ' max deviation px', hang.maxDev);
  if (hang.nOff) console.log(hang.off);
  // exact word-level check: every source token must be present in the rendered DOM (and nothing extra)
  const domTokens = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('.ln, .tblband td, .tblband th').forEach((el) => {
      const c = el.cloneNode(true); c.querySelectorAll('.fnref').forEach((x) => x.remove());
      out.push(...c.textContent.split(/\s+/).filter(Boolean));
    });
    return out;
  });
  const cnt = (arr) => { const m = new Map(); for (const t of arr) m.set(t, (m.get(t) || 0) + 1); return m; };
  const srcTokens = [];
  const addRuns = (runs) => srcTokens.push(...runs.filter((r) => r.fn === undefined).map((r) => r.t).join('').split(/\s+/).filter(Boolean));
  for (const a of doc.articles) {
    for (const bl of a.blocks) {
      if (bl.t === 'tbl') bl.rows.forEach((row) => row.forEach((cell) => addRuns(cell)));
      else addRuns(bl.runs);
    }
    const used = new Set();
    for (const bl of a.blocks) if (bl.t !== 'tbl') for (const r of bl.runs) if (r.fn !== undefined) used.add(r.fn);
    for (const id of used) if (a.footnotes[id]) addRuns(a.footnotes[id]);
  }
  const cs = cnt(srcTokens), cd = cnt(domTokens);
  const diffs = [];
  for (const [k, v] of cs) if ((cd.get(k) || 0) !== v) diffs.push(['src', k, v, cd.get(k) || 0]);
  for (const [k, v] of cd) if (!cs.has(k)) diffs.push(['dom-only', k, 0, v]);
  console.log('word check: source tokens', srcTokens.length, 'dom tokens', domTokens.length, 'differences', diffs.length);
  if (diffs.length) console.log(diffs.slice(0, 15));
  console.log('pages:', res.pages, ' overflowing lines:', check.length);
  if (check.length) console.log(check.slice(0, 8));
  fs.writeFileSync(outPdf.replace(/\.pdf$/, '.layout.json'), JSON.stringify(res, null, 1));
  await page.pdf({ path: outPdf, width: '176mm', height: '250mm', printBackground: true, preferCSSPageSize: true });
  await browser.close();
})();
