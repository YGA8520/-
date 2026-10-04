#!/usr/bin/env node
/* usage: node build.js doc.json out.pdf [config.json]   -> also writes out.json with layout stats */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
(async () => {
  const [,, docPath, outPdf, cfgPath = path.join(__dirname, 'config.json')] = process.argv;
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const doc = JSON.parse(fs.readFileSync(docPath, 'utf8'));
  if (process.env.DEBUG_TOC) cfg.debugToc = true;
  // ---- fonts: roles (body / lead / display) and the font files that provide them -> config.json "fonts" and "fontFaces"
  const F = cfg.fonts = Object.assign({ body: 'Frank Ruhl Libre', lead: 'David Libre', display: 'Frank Ruhl Libre' }, cfg.fonts || {});
  F.notes = F.notes || F.body; F.author = F.author || F.lead; F.toc = F.toc || F.body;
  const WD = (cfg.fontWeights || {}).display || 800;                 // weight of the display (title) role: 800 for a variable family, 400 for a single-weight calligraphic face
  const WL = (cfg.fontWeights || {}).lead || 700;
  cfg.titleFrame.weight = WD; cfg.dividerFrame.weight = WD; cfg.type.h2.weight = WD; cfg.type.h3.weight = WL; cfg.fontWeights = { display: WD, lead: WL };      // roles: body, lead (first word / sub-headings), display (titles), notes (footnotes), author (author names)
  Object.assign(cfg.type.body, { family: F.body }); Object.assign(cfg.type.foot, { family: F.notes });
  Object.assign(cfg.type.h2, { family: F.display }); Object.assign(cfg.type.h3, { family: F.lead });
  Object.assign(cfg.type.lead, { family: F.lead }); Object.assign(cfg.type.abstract, { family: F.lead });
  Object.assign(cfg.titleFrame, { family: F.display }); Object.assign(cfg.dividerFrame, { family: F.display });
  cfg.footnotes.titleFamily = F.notes;
  const faces = cfg.fontFaces || [];
  if (cfg.cover) {            // the artwork cover (make_cover.py writes the background); without it the plain placeholder cover is used
    cfg.cover.enabled = fs.existsSync(path.join(__dirname, cfg.cover.image));
    cfg.cover.colors = (cfg.cover.palettes || {})[cfg.cover.palette] || Object.values(cfg.cover.palettes || {})[0];
    if (!cfg.cover.enabled) console.log('note: cover background', cfg.cover.image, 'not found (run make_cover.py) - placeholder cover used');
  }
  if (cfg.divider) cfg.divider.enabled = !!(cfg.cover && cfg.cover.enabled) && fs.existsSync(path.join(__dirname, cfg.divider.image));
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
  const styleCss = `:root{--f-body:"${F.body}";--f-lead:"${F.lead}";--f-display:"${F.display}";--f-notes:"${F.notes}";--f-author:"${F.author}";--f-toc:"${F.toc}";--w-notes:${cfg.type.foot.weight || 400};--s-foot:${cfg.type.foot.size};--w-display:${WD};--w-lead:${WL};}\n` +
    faces.map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};font-style:${f.style || 'normal'};${f.unicodeRange ? 'unicode-range:' + f.unicodeRange + ';' : ''}src:url("assets/fonts/${f.file}");}`).join('\n');
  await page.addStyleTag({ content: styleCss });
  await page.addScriptTag({ path: path.join(__dirname, 'engine.js') });
  await page.evaluate(async (fontSpecs) => {
    await Promise.all(fontSpecs.map((f) => document.fonts.load(f, 'אבג')));
    await document.fonts.ready;
  }, [400, 700, 800].flatMap((w) => [F.body, F.lead, F.display, F.notes, F.author, F.toc, ...(cfg.cover ? [cfg.cover.fontTitle, cfg.cover.fontArc, cfg.cover.fontLines] : [])].map((fam) => `${w} 16px "${fam}"`)));
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
      pg.querySelectorAll('.tocwrap').forEach((el) => {          // table-of-contents pages: the last row (or the end ornament) must stay on the page
        const bottom = el.lastElementChild.getBoundingClientRect().bottom - pg.getBoundingClientRect().top;
        if (bottom > H - 14) bad.push('pdf page ' + (i + 1) + ': table of contents runs off the page');
      });
    });
    return bad;
  });
  console.log('vertical overflow: lines below the page text area:', vover.length);
  if (vover.length) console.log(vover.slice(0, 8));
  // stray lines: one line of a paragraph alone at the top / foot of a column; a last line holding a single word
  const stray = await page.evaluate(() => {
    const widow = [], orphan = [], oneword = [];
    document.querySelectorAll('.page').forEach((pg, pi) => {
      const ls = [...pg.querySelectorAll('.ln[data-pn]')];
      ls.forEach((el, i) => {
        const pn = +el.dataset.pn, idx = +el.dataset.pi, tp = parseFloat(el.style.top);
        const prev = ls[i - 1], next = ls[i + 1];
        const firstInCol = !prev || parseFloat(prev.style.top) >= tp;
        const lastInCol = !next || parseFloat(next.style.top) <= tp;
        if (pn > 1 && idx === pn - 1 && firstInCol && el.dataset.lw && !el.classList.contains('c-foot')) widow.push('pdf p.' + (pi + 1) + ': ' + el.textContent.slice(0, 24));
        if (pn > 1 && idx === 0 && lastInCol && !el.classList.contains('c-foot')) orphan.push('pdf p.' + (pi + 1) + ': ' + el.textContent.slice(0, 24));
        if (pn > 1 && idx === pn - 1 && +el.dataset.lw === 1 && !el.classList.contains('c-foot')) oneword.push('pdf p.' + (pi + 1) + ': ' + el.textContent.slice(0, 24));
      });
    });
    return { widow, orphan, oneword };
  });
  console.log('stray lines: widows at column top', stray.widow.length, ' orphans at column foot', stray.orphan.length, ' one-word last lines', stray.oneword.length);
  for (const k of ['widow', 'orphan', 'oneword']) if (stray[k].length) console.log(k, stray[k].slice(0, 6));
  if (process.env.DUMP_PAGES) {            // debugging aid: DUMP_PAGES=223,287 prints the lines of those pdf pages
    const want = process.env.DUMP_PAGES.split(',').map(Number);
    const dump = await page.evaluate((want) => want.map((p) => {
      const pg = document.querySelectorAll('.page')[p - 1];
      return 'pdf page ' + p + '\n' + [...pg.querySelectorAll('.ln')].map((el) => (el.dataset.pn ? el.dataset.pi + '/' + el.dataset.pn + ' w' + el.dataset.lw : '-') + ' y' + Math.round(parseFloat(el.style.top)) + ' x' + Math.round(parseFloat(el.style.left)) + ' ' + el.textContent.slice(0, 28)).join('\n');
    }), want);
    console.log(dump.join('\n'));
  }
  if (process.env.DUMP_FONTS) {            // debugging aid: which font role / weight each piece of text really uses
    const fu = await page.evaluate(() => {
      const m = {};
      document.querySelectorAll('.page *').forEach((el) => {
        const t = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join('').trim();
        if (!t) return;
        const cs = getComputedStyle(el), k = cs.fontFamily.split(',')[0].replace(/"/g, '') + ' ' + cs.fontWeight;
        (m[k] = m[k] || { n: 0, s: [] }).n++;
        if (m[k].s.length < 2) m[k].s.push(t.slice(0, 24) + ' <' + el.tagName.toLowerCase() + '.' + el.className + ' < ' + (el.parentElement.className || el.parentElement.tagName) + '>');
      });
      return m;
    });
    console.log('fonts in use:', JSON.stringify(fu, null, 1));
  }
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
  if (cfg.cover && cfg.cover.enabled && !doc.noCover) {          // the cover alone: a 300 dpi picture (used in the Word file) and a one-page pdf
    const outDir = path.dirname(outPdf);
    const cp = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 2079 / (176 * 96 / 25.4) });
    await cp.goto('file://' + path.join(__dirname, 'template.html'));
    await cp.addStyleTag({ content: styleCss });
    await cp.addScriptTag({ path: path.join(__dirname, 'engine.js') });
    await cp.evaluate(async (fams) => { await Promise.all(fams.flatMap((f) => [400, 700].map((w) => document.fonts.load(w + ' 16px "' + f + '"', 'אבג')))); await document.fonts.ready; }, [cfg.cover.fontTitle, cfg.cover.fontArc, cfg.cover.fontLines]);
    await cp.evaluate(([c, name]) => {
      document.body.style.margin = '0';
      document.body.innerHTML = '<div id="cv" class="page cover" style="width:176mm;height:250mm;position:relative;overflow:hidden">' + window.coverHTML(c, name) + '</div>';
    }, [cfg, doc.book.name]);
    await cp.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))));
    await cp.locator('#cv').screenshot({ path: path.join(outDir, 'cover.jpg'), type: 'jpeg', quality: 93 });
    await cp.pdf({ path: path.join(outDir, 'cover.pdf'), width: '176mm', height: '250mm', printBackground: true, preferCSSPageSize: true });
  }
  if (cfg.divider && cfg.divider.enabled && res.dividers && res.dividers.length) {          // one picture per internal title page (used in the Word file)
    const outDir = path.join(path.dirname(outPdf), 'dividers');
    fs.mkdirSync(outDir, { recursive: true });
    for (const f of fs.readdirSync(outDir)) if (/^div-\d+\.jpg$/.test(f)) fs.unlinkSync(path.join(outDir, f));        // no stale pictures of earlier builds
    const dp = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 1450 / (176 * 96 / 25.4) });
    await dp.goto('file://' + path.join(__dirname, 'template.html'));
    await dp.addStyleTag({ content: styleCss });
    await dp.addScriptTag({ path: path.join(__dirname, 'engine.js') });
    await dp.evaluate(async (fams) => { await Promise.all(fams.flatMap((f) => [400, 700].map((w) => document.fonts.load(w + ' 16px "' + f + '"', 'אבג')))); await document.fonts.ready; }, [cfg.cover.fontTitle, cfg.cover.fontArc, cfg.cover.fontLines]);
    for (const d of res.dividers) {
      await dp.evaluate(([c, label, name]) => {
        document.body.style.margin = '0';
        document.body.innerHTML = '<div id="cv" class="page cover" style="width:176mm;height:250mm;position:relative;overflow:hidden">' + window.dividerHTML(c, label, name) + '</div>';
      }, [cfg, d.label, doc.book.name]);
      await dp.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))));
      await dp.locator('#cv').screenshot({ path: path.join(outDir, `div-${d.ai}.jpg`), type: 'jpeg', quality: 86 });
    }
  }
  await browser.close();
})();
