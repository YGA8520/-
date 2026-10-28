// node eliyahu/build.js out_dir  -> page1.pdf (80 x 110 mm) + page1.png (600 dpi preview)
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const out = process.argv[2] || 'out/eliyahu'; fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ deviceScaleFactor: 600 / 96 });
  await p.goto('file://' + path.resolve(__dirname, 'page1.html')); await p.evaluate(() => document.fonts.ready);
  const over = await p.evaluate(() => { const pg = document.querySelector('.page'); return pg.scrollHeight - pg.clientHeight; });
  console.log('vertical overflow px:', over);
  await p.pdf({ path: path.join(out, 'page1.pdf'), width: '80mm', height: '110mm', printBackground: true, preferCSSPageSize: true });
  await p.setViewportSize({ width: Math.round(80 / 25.4 * 96), height: Math.round(110 / 25.4 * 96) });
  await p.screenshot({ path: path.join(out, 'page1.png') }); await b.close();
})();
