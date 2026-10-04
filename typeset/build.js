#!/usr/bin/env node
/* usage: node build.js doc.json out.pdf [config.json]   -> also writes out.json with layout stats */
const fs = require('fs'), path = require('path');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const [,, docPath, outPdf, cfgPath = path.join(__dirname, 'config.json')] = process.argv;
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const doc = JSON.parse(fs.readFileSync(docPath, 'utf8'));
  // ---- fonts: roles (body / lead / display) and the font files that provide them -> config.json "fonts" and "fontFaces"
  const F = cfg.fonts = Object.assign({ body: 'Frank Ruhl Libre', lead: 'David Libre', display: 'Frank Ruhl Libre' }, cfg.fonts || {});
  Object.assign(cfg.type.body, { family: F.body }); Object.assign(cfg.type.foot, { family: F.body });
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
  await page.addStyleTag({ content: `:root{--f-body:"${F.body}";--f-lead:"${F.lead}";--f-display:"${F.display}";}\n` +
    faces.map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};font-style:${f.style || 'normal'};src:url("assets/fonts/${f.file}");}`).join('\n') });
  await page.addScriptTag({ path: path.join(__dirname, 'engine.js') });
  await page.evaluate(async (fontSpecs) => {
    await Promise.all(fontSpecs.map((f) => document.fonts.load(f, 'אבג')));
    await document.fonts.ready;
  }, [400, 700, 800].flatMap((w) => [F.body, F.lead, F.display].map((fam) => `${w} 16px "${fam}"`)));
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
