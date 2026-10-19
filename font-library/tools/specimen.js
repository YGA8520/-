#!/usr/bin/env node
/* usage: node tools/specimen.js [fonts-dir] [out-dir]
   Renders one PNG per family (Hebrew + Latin + digits, every weight/italic found) so a font can be chosen by eye.
   Uses the same Chromium/Playwright as the rest of the repo. */
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const ROOT = path.resolve(__dirname, '..');
const fontsDir = path.resolve(process.argv[2] || path.join(ROOT, 'my-fonts', 'fonts'));
const outDir = path.resolve(process.argv[3] || path.join(ROOT, 'specimens'));
const catalog = JSON.parse(fs.readFileSync(path.join(ROOT, 'my-fonts', 'catalog.json'), 'utf8')).families;
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const HEB = 'בראשית ברא אלקים את השמים ואת הארץ — אבגדהוזחטיכךלמםנןסעפףצץקרשת 0123456789 ₪ ״׳';
const LAT = 'The quick brown fox jumps over the lazy dog — ABCDEFG abcdefg 0123456789';
(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  for (const [fam, { fonts }] of Object.entries(catalog)) {
    let css = '', rows = '';
    fonts.forEach((f, i) => {
      const file = f.file.split('#')[0];
      const src = 'file://' + path.join(ROOT, 'my-fonts', file).replace(/ /g, '%20');
      const w = f.variable_axes && f.variable_axes.wght ? `${f.variable_axes.wght[0]} ${f.variable_axes.wght[2]}` : f.weight;
      css += `@font-face{font-family:"S${i}";src:url("${src}");font-weight:${w};font-style:${f.italic ? 'italic' : 'normal'}}\n`;
      rows += `<div class="row"><div class="tag">${esc(f.style)} · ${f.weight}${f.italic ? ' italic' : ''}${f.variable_axes && f.variable_axes.wght ? ' · variable' : ''} · ${esc(f.file)}</div>
        <div class="heb" style="font-family:'S${i}';font-weight:${f.weight};font-style:${f.italic ? 'italic' : 'normal'}">${HEB}</div>
        <div class="lat" style="font-family:'S${i}';font-weight:${f.weight};font-style:${f.italic ? 'italic' : 'normal'}">${LAT}</div></div>`;
    });
    const html = `<!doctype html><meta charset=utf-8><style>${css}
      body{margin:0;padding:28px 36px;width:1100px;background:#fff;color:#111;font:13px sans-serif}
      h1{font:600 20px sans-serif;margin:0 0 14px;direction:ltr}
      .row{border-top:1px solid #ccc;padding:10px 0}.tag{color:#777;font-size:11px;direction:ltr;margin-bottom:6px}
      .heb{direction:rtl;font-size:34px;line-height:1.35}.lat{direction:ltr;font-size:26px;line-height:1.3;margin-top:4px}</style>
      <h1>${esc(fam)}</h1>${rows}`;
    const page = await browser.newPage({ viewport: { width: 1180, height: 400 } });
    await page.setContent(html, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    const out = path.join(outDir, fam.replace(/[^\w-]+/g, '_') + '.png');
    await page.screenshot({ path: out, fullPage: true });
    await page.close();
    console.log('wrote', path.relative(ROOT, out));
  }
  await browser.close();
})();
