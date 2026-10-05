#!/usr/bin/env node
/* usage: node front_pages.js [booklet.json] [out_dir] [--only=cover,inner,credits,back]
   The covers of a booklet in the layout of this repo, without typesetting a book: outer cover, the empty page behind it, inner title page, credits page and back cover.
   booklet.json is an overlay on config.json (default booklets/lechidoda.json): "bookName" (the title, first word on the first line), "cover.texts", "innerCover.texts",
   "credits.items", "fontFaces" ... Objects are merged, arrays replaced (fontFaces: by family + weight).  A font face may name a "fallback" file that is used when the
   (proprietary, not in git) file is missing, so the pages can be built anywhere; use the real fonts for the final files (see README).
   writes into out_dir (default ../output/<booklet name>): 1-outer-cover / 2-empty-page / 3-inner-cover / 4-credits / 5-back-cover as .pdf (vector text, 176 x 250 mm) and .jpg (300 dpi),
   and all-pages.pdf (the five pages in one file, in the order of the booklet). */
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const isObj = (x) => x && typeof x === 'object' && !Array.isArray(x);
function merge(a, b) {
  const out = Object.assign({}, a);
  for (const [k, v] of Object.entries(b)) {
    if (k === 'fontFaces') {                                       // by family + weight (+ unicode range)
      const key = (f) => [f.family, f.weight || 400, f.unicodeRange || ''].join('|'), m = new Map((a.fontFaces || []).map((f) => [key(f), f]));
      for (const f of v) m.set(key(f), f);
      out.fontFaces = [...m.values()];
    } else out[k] = isObj(v) && isObj(a[k]) ? merge(a[k], v) : v;
  }
  return out;
}

(async () => {
  const args = process.argv.slice(2), flags = args.filter((a) => a.startsWith('--')), pos = args.filter((a) => !a.startsWith('--'));
  const bookletPath = path.resolve(pos[0] || path.join(__dirname, 'booklets', 'lechidoda.json'));
  const base = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
  const cfg = merge(base, JSON.parse(fs.readFileSync(bookletPath, 'utf8')));
  const bookName = cfg.bookName;
  const outDir = path.resolve(pos[1] || path.join(__dirname, '..', 'output', path.basename(bookletPath, '.json')));
  fs.mkdirSync(outDir, { recursive: true });
  const only = (flags.find((f) => f.startsWith('--only=')) || '').slice(7).split(',').filter(Boolean);

  cfg.cover.colors = cfg.cover.palettes[cfg.cover.palette];
  if (cfg.innerCover && cfg.divider && cfg.divider.colors) cfg.innerCover.colors = cfg.innerCover.colors || cfg.divider.colors;
  const need = [cfg.cover.image, cfg.innerCover.image, cfg.credits.image, cfg.backCover.image];
  for (const f of need) if (!fs.existsSync(path.join(__dirname, f))) throw new Error(`missing artwork ${f} (run make_cover.py / make_divider.py)`);

  const fams = [...new Set([cfg.cover.fontTitle, cfg.cover.fontArc, cfg.cover.fontArcTop, cfg.cover.fontLines, cfg.fonts.notes].filter(Boolean))];
  // font faces: the real file when it exists, else the fallback; one @font-face per face with both sources listed (the browser takes the first that loads)
  const have = (f) => fs.existsSync(path.join(__dirname, 'assets', 'fonts', f));
  const used = [];
  const css = cfg.fontFaces.map((f) => {
    const srcs = [f.file, f.fallback].filter(Boolean).filter(have);
    const real = srcs[0] === f.file, w = real ? (f.weight || 400) : (f.fallbackWeight || f.weight || 400);          // a substitute may need another weight to match the colour of the original
    if (!srcs.length) { if (fams.includes(f.family)) console.log(`note: font ${f.family} ${f.weight || 400} (${f.file}) not found`); return ''; }
    if (fams.includes(f.family)) used.push(`${f.family} ${w}: ${srcs[0]}${real ? '' : '  (substitute - the original font file ' + f.file + ' is missing)'}`);
    return `@font-face{font-family:"${f.family}";font-weight:${w};font-style:normal;${f.unicodeRange ? 'unicode-range:' + f.unicodeRange + ';' : ''}src:${srcs.map((s) => `url("assets/fonts/${s}")`).join(',')};}`;
  }).join('\n');
  console.log('fonts:\n  ' + used.join('\n  '));

  const pages = [
    ['cover', '1-outer-cover', (c, n) => window.coverHTML(c, n)],
    ['empty', '2-empty-page', () => ''],
    ['inner', '3-inner-cover', (c, n) => window.innerCoverHTML(c, n)],
    ['credits', '4-credits', (c, n) => window.creditsHTML(c, n)],
    ['back', '5-back-cover', (c) => window.backCoverHTML(c)],
  ];
  const browser = await chromium.launch();
  const open = async (scale) => {
    const p = await browser.newPage({ viewport: { width: 700, height: 1000 }, deviceScaleFactor: scale });
    p.on('pageerror', (e) => console.log('[pageerror]', e.message));
    await p.goto('file://' + path.join(__dirname, 'template.html'));
    await p.addStyleTag({ content: css });
    await p.addScriptTag({ path: path.join(__dirname, 'engine.js') });
    await p.evaluate(async (fs_) => { await Promise.all(fs_.flatMap((f) => [400, 700].map((w) => document.fonts.load(w + ' 16px "' + f + '"', 'אבג')))); await document.fonts.ready; }, fams);
    return p;
  };
  const fill = async (p, htmls) => {
    await p.evaluate((hs) => {
      document.body.style.margin = '0';
      document.body.innerHTML = hs.map((h, i) => `<div class="page cover" id="pg${i}" style="width:176mm;height:250mm;position:relative;overflow:hidden">${h}</div>`).join('');
    }, htmls);
    await p.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))));
    await p.evaluate(() => document.fonts.ready);
  };
  const html = async (p, fn) => p.evaluate(([f, c, n]) => eval('(' + f + ')')(c, n), [fn.toString(), cfg, bookName]);

  const sp = await open(2079 / (176 * 96 / 25.4));            // 300 dpi pictures
  const all = [];
  for (const [key, name, fn] of pages) {
    const h = await html(sp, fn);
    all.push(h);
    if (only.length && !only.includes(key)) continue;
    await fill(sp, [h]);
    await sp.locator('#pg0').screenshot({ path: path.join(outDir, name + '.jpg'), type: 'jpeg', quality: 93 });
    await sp.pdf({ path: path.join(outDir, name + '.pdf'), width: '176mm', height: '250mm', printBackground: true, preferCSSPageSize: true });
    console.log('written', name);
  }
  if (!only.length) {
    await fill(sp, all);
    await sp.pdf({ path: path.join(outDir, 'all-pages.pdf'), width: '176mm', height: '250mm', printBackground: true, preferCSSPageSize: true });
    console.log('written all-pages.pdf');
  }
  await browser.close();
  const pdfs = fs.readdirSync(outDir).filter((f) => f.endsWith('.pdf')).map((f) => path.join(outDir, f));
  try { execFileSync(process.platform === 'win32' ? 'python' : 'python3', [path.join(__dirname, 'trim_pdf.py'), ...pdfs]); console.log('pdf page boxes set to 176 x 250 mm'); }
  catch (e) { console.log('note: trim_pdf.py failed (pip install pypdf) - the pdf pages keep the size Chromium gave them (498.96 x 708.96 pt):', e.message.split('\n')[0]); }
})();
