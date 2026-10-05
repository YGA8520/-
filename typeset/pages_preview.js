#!/usr/bin/env node
/* usage: node pages_preview.js out_dir   -> out_dir/inner-cover.png and out_dir/credits.png (the inner title page and the credits page, as they will be in the booklet) */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
(async () => {
  const outDir = process.argv[2] || 'out';
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
  const doc = JSON.parse(fs.readFileSync(path.join(__dirname, 'book.doc.json'), 'utf8'));
  cfg.cover.colors = cfg.cover.palettes[cfg.cover.palette];
  if (cfg.innerCover && !cfg.innerCover.colors) cfg.innerCover.colors = cfg.divider.colors;
  const css = (cfg.fontFaces || []).map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};src:url("assets/fonts/${f.file}");}`).join('\n');
  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, 'template.html'));
  await p.addStyleTag({ content: css });
  await p.addScriptTag({ path: path.join(__dirname, 'engine.js') });
  await p.evaluate(async (f) => { await Promise.all(f.flatMap((x) => [400, 700].map((w) => document.fonts.load(w + ' 16px "' + x + '"', 'אבג')))); }, [cfg.cover.fontTitle, cfg.cover.fontArc, cfg.cover.fontLines, cfg.fonts.body, cfg.fonts.display, cfg.fonts.lead]);
  for (const [fn, file] of [['innerCoverHTML', 'inner-cover.png'], ['creditsHTML', 'credits.png']]) {
    await p.evaluate(([c, n, f]) => { document.body.style.margin = '0'; document.body.innerHTML = '<div id="cv" class="page cover" style="width:176mm;height:250mm;position:relative;overflow:hidden">' + window[f](c, n) + '</div>'; }, [cfg, doc.book.name, fn]);
    await p.evaluate(() => Promise.all([...document.images].map((im) => im.decode().catch(() => {}))));
    await p.locator('#cv').screenshot({ path: path.join(outDir, file) });
  }
  await browser.close();
})();
