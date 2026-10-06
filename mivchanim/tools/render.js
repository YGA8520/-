// Render HTML files to PDF / PNG with Chromium.
// usage: node tools/render.js jobs.json
// job: { html, pdf?, png?, pngs?: {prefix, clip?}, width_mm?, height_mm?, scale? , wait? }
const path = require('path');
const fs = require('fs');
let playwright;
try { playwright = require('playwright'); } catch (e) { playwright = require('/opt/node-tools/node_modules/playwright'); }

(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await playwright.chromium.launch({
    executablePath: process.env.CHROME || undefined,
    args: ['--no-sandbox', '--font-render-hinting=none', '--allow-file-access-from-files'],
  });
  for (const j of jobs) {
    const ctx = await browser.newContext({ deviceScaleFactor: j.scale || 1, viewport: { width: j.vw || 794, height: j.vh || 1123 } });
    const page = await ctx.newPage();
    page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('console', m.type(), m.text()); });
    page.on('pageerror', (e) => console.log('pageerror', e.message));
    await page.goto('file://' + path.resolve(j.html), { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    if (j.eval) { await page.evaluate(j.eval); await page.waitForTimeout(100); }
    await page.waitForTimeout(j.wait || 200);
    if (j.pdf) {
      await page.pdf({ path: j.pdf, width: (j.width_mm || 210) + 'mm', height: (j.height_mm || 297) + 'mm', printBackground: true, preferCSSPageSize: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
    }
    if (j.png) {
      await page.screenshot({ path: j.png, fullPage: true });
    }
    if (j.info) {
      const info = await page.evaluate(new Function('return (' + j.info + ')()'));
      fs.writeFileSync(j.infoOut, JSON.stringify(info, null, 1));
    }
    await ctx.close();
    console.log('rendered', j.pdf || j.png);
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
