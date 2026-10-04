#!/usr/bin/env node
/* usage: node build.js doc.json out.pdf [config.json]   -> also writes out.json with layout stats */
const fs = require('fs'), path = require('path');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const [,, docPath, outPdf, cfgPath = path.join(__dirname, 'config.json')] = process.argv;
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const doc = JSON.parse(fs.readFileSync(docPath, 'utf8'));
  cfg.ornaments = {};
  for (const k of ['top', 'bottom', 'end']) {
    const f = path.join(__dirname, 'assets', 'ornaments', k + '.svg');
    if (fs.existsSync(f)) cfg.ornaments[k] = fs.readFileSync(f, 'utf8');
  }
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', (m) => console.log('[page]', m.text()));
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto('file://' + path.join(__dirname, 'template.html'));
  await page.addScriptTag({ path: path.join(__dirname, 'engine.js') });
  await page.evaluate(async () => {
    await Promise.all(['400 16px "David Libre"', '700 16px "David Libre"', '800 16px "Frank Ruhl Libre"', '700 16px "Frank Ruhl Libre"'].map((f) => document.fonts.load(f, 'אבג')));
    await document.fonts.ready;
  });
  const res = await page.evaluate(([c, d]) => window.typeset(c, d), [cfg, doc]);
  const check = await page.evaluate(() => {
    const bad = [];
    document.querySelectorAll('.ln').forEach((el) => { if (el.scrollWidth > el.clientWidth + 1.5) bad.push(el.textContent.slice(0, 40) + ' ' + el.scrollWidth + '>' + el.clientWidth); });
    return bad;
  });
  console.log('pages:', res.pages, ' overflowing lines:', check.length);
  if (check.length) console.log(check.slice(0, 8));
  fs.writeFileSync(outPdf.replace(/\.pdf$/, '.layout.json'), JSON.stringify(res, null, 1));
  await page.pdf({ path: outPdf, width: '176mm', height: '250mm', printBackground: true, preferCSSPageSize: true });
  await browser.close();
})();
