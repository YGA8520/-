// node eliyahu/build.js out_dir [page]  -> <page>.pdf (80 x 110 mm) + <page>.png (600 dpi preview); page = page1 (grey) | page1-color
// BLEED=3 node eliyahu/build.js out_dir page1-color  -> <page>-bleed.pdf: (80 + 2*3) x (110 + 2*3) mm, the artwork runs into
//   the bleed (bg-color-bleed.jpg, make_bleed_bg.py); make_print_sheet.py then adds the crop marks and the PDF boxes
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
  const bleed = parseFloat(process.env.BLEED || 0);
  if (bleed) {
    const W = 80 + 2 * bleed, H = 110 + 2 * bleed;
    await p.addStyleTag({ content: `@page { size: ${W}mm ${H}mm; margin: 0; }
      .page { overflow: visible; margin: ${bleed}mm; }
      .bg { inset: auto; left: -${bleed}mm; top: -${bleed}mm; width: ${W}mm; height: ${H}mm; }` });
    await p.evaluate(() => { const bg = document.querySelector('.bg'); bg.src = bg.src.replace('bg-color.jpg', 'bg-color-bleed.jpg');
      return new Promise(r => bg.complete ? r() : bg.onload = r); });
    await p.pdf({ path: path.join(out, name + '-bleed.pdf'), width: W + 'mm', height: H + 'mm', printBackground: true, preferCSSPageSize: true });
    await b.close(); return;
  }
  await p.pdf({ path: path.join(out, name + '.pdf'), width: '80mm', height: '110mm', printBackground: true, preferCSSPageSize: true });
  await p.setViewportSize({ width: Math.round(80 / 25.4 * 96), height: Math.round(110 / 25.4 * 96) });
  await p.screenshot({ path: path.join(out, name + '.png') }); await b.close();
})();
