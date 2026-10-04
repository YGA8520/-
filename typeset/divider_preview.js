#!/usr/bin/env node
/* usage: node divider_preview.js out_dir [bg.jpg] [label ...]  -> out_dir/div-<n>.png : the internal title pages for the given labels (default: 4 samples) */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
(async () => {
  const outDir = process.argv[2] || 'out';
  const bg = process.argv[3] || path.join(outDir, 'bg.jpg');
  const labels = process.argv.length > 4 ? process.argv.slice(4) : ['סימן ד׳', 'סימן ס״ו', 'סימן תפ״ט', 'יורה דעה סימן של״ד', 'פתיחות'];
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
  const doc = JSON.parse(fs.readFileSync(path.join(__dirname, 'book.doc.json'), 'utf8'));
  cfg.cover.colors = cfg.cover.palettes[cfg.cover.palette];
  cfg.divider.image = path.relative(__dirname, path.resolve(bg)).replace(/\\/g, '/');
  const css = (cfg.fontFaces || []).map((f) => `@font-face{font-family:"${f.family}";font-weight:${f.weight || 400};src:url("assets/fonts/${f.file}");}`).join('\n');
  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, 'template.html'));
  await p.addStyleTag({ content: css });
  await p.addScriptTag({ path: path.join(__dirname, 'engine.js') });
  await p.evaluate(async (f) => { await Promise.all(f.flatMap((x) => [400, 700].map((w) => document.fonts.load(w + ' 16px "' + x + '"', 'אבג')))); }, [cfg.cover.fontTitle, cfg.cover.fontArc, cfg.cover.fontLines]);
  for (let i = 0; i < labels.length; i++) {
    await p.evaluate(([cc, n, l]) => { document.body.style.margin = '0'; document.body.innerHTML = '<div id="cv" class="page cover" style="width:176mm;height:250mm;position:relative;overflow:hidden">' + window.dividerHTML(cc, l, n) + '</div>'; }, [cfg, doc.book.name, labels[i]]);
    await p.evaluate(() => Promise.all([...document.images].map((im) => im.decode().catch(() => {}))));
    await p.locator('#cv').screenshot({ path: path.join(outDir, `div-${i}.png`) });
  }
  await browser.close();
})();
