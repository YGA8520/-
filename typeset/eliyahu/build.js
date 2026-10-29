// node eliyahu/build.js out_dir [page]  -> <page>.pdf (80 x 110 mm) + <page>.png (600 dpi preview); page = page1 (grey) | page1-color
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const out = process.argv[2] || 'out/eliyahu', name = process.argv[3] || 'page1'; fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ deviceScaleFactor: 600 / 96 });
  await p.goto('file://' + path.resolve(__dirname, name + '.html')); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(150);
  // overflow = how far the last block reaches below the padding of the box that must hold the text
  // ([data-fit], else the page) in mm; free = height of the spacer
  const m = await p.evaluate(() => { const pg = document.querySelector('[data-fit]') || document.querySelector('.page'), k = 25.4 / 96;
    const bottom = pg.getBoundingClientRect().bottom - parseFloat(getComputedStyle(pg).paddingBottom);
    return { overflow: ((pg.lastElementChild.getBoundingClientRect().bottom - bottom) * k).toFixed(2),
             free: (document.querySelector('.spacer').getBoundingClientRect().height * k).toFixed(2) }; });
  console.log('overflow mm:', m.overflow, ' free space mm:', m.free);
  await p.pdf({ path: path.join(out, name + '.pdf'), width: '80mm', height: '110mm', printBackground: true, preferCSSPageSize: true });
  await p.setViewportSize({ width: Math.round(80 / 25.4 * 96), height: Math.round(110 / 25.4 * 96) });
  await p.screenshot({ path: path.join(out, name + '.png') }); await b.close();
})();
