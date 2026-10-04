#!/usr/bin/env node
/* usage: node cover_preview.js out_dir   -> out_dir/cover-<palette>.png for every palette of config.json (needs assets/cover/cover-bg-<palette>.jpg made by `python make_cover.py <palette> <file>`) */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
(async () => {
  const outDir = process.argv[2] || 'out';
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
  const doc = JSON.parse(fs.readFileSync(path.join(__dirname, 'book.doc.json'), 'utf8'));
  const css = (cfg.fontFaces || []).map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};src:url("assets/fonts/${f.file}");}`).join('\n');
  const browser = await chromium.launch();
  for (const pal of Object.keys(cfg.cover.palettes)) {
    const bg = path.join(outDir, `cover-bg-${pal}.jpg`);
    if (!fs.existsSync(bg)) continue;
    const c = JSON.parse(JSON.stringify(cfg)); c.cover.image = path.relative(__dirname, path.resolve(bg)).replace(/\\/g, '/'); c.cover.colors = c.cover.palettes[pal];
    const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 1.5 });
    await p.goto('file://' + path.join(__dirname, 'template.html'));
    await p.addStyleTag({ content: css });
    await p.addScriptTag({ path: path.join(__dirname, 'engine.js') });
    await p.evaluate(async (f) => { await Promise.all(f.flatMap((x) => [400, 700].map((w) => document.fonts.load(w + ' 16px "' + x + '"', 'אבג')))); }, [c.cover.fontTitle, c.cover.fontText]);
    await p.evaluate(([cc, n]) => { document.body.style.margin = '0'; document.body.innerHTML = '<div id="cv" class="page cover" style="width:176mm;height:250mm;position:relative;overflow:hidden">' + window.coverHTML(cc, n) + '</div>'; }, [c, doc.book.name]);
    await p.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))));
    await p.locator('#cv').screenshot({ path: path.join(outDir, `cover-${pal}.png`) });
    await p.close();
  }
  await browser.close();
})();
