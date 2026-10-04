/* Hebrew sefer-style typesetting engine (runs inside Chromium).
 *
 *   window.typeset(cfg, doc)  ->  builds <div class="page"> elements in #pages
 *
 * Line breaking is done here (Knuth-Plass style, no hyphenation), every line is then placed
 * absolutely, so columns, footnotes and header all sit on an exact grid.  Chromium prints it to PDF.
 */
(function () {
  const MM = 96 / 25.4, PT = 96 / 72;
  const mm = (x) => x * MM, pt = (x) => x * PT;

  // ---------------------------------------------------------------- helpers
  function heb(n) {
    if (n === 15) return 'טו';
    if (n === 16) return 'טז';
    const L = [[400, 'ת'], [300, 'ש'], [200, 'ר'], [100, 'ק'], [90, 'צ'], [80, 'פ'], [70, 'ע'], [60, 'ס'], [50, 'נ'], [40, 'מ'], [30, 'ל'], [20, 'כ'], [10, 'י'], [9, 'ט'], [8, 'ח'], [7, 'ז'], [6, 'ו'], [5, 'ה'], [4, 'ד'], [3, 'ג'], [2, 'ב'], [1, 'א']];
    let s = '';
    for (const [v, c] of L) while (n >= v) { s += c; n -= v; }
    if (s.endsWith('טו') || s.endsWith('טז')) return s;
    return s;
  }
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // ---------------------------------------------------------------- measurement
  const cv = document.createElement('canvas').getContext('2d');
  cv.textRendering = 'geometricPrecision'; cv.fontKerning = 'normal';
  const wcache = new Map();
  function textW(text, font) {
    const k = font + '|' + text;
    let w = wcache.get(k);
    if (w === undefined) { cv.font = font; w = cv.measureText(text).width; wcache.set(k, w); }
    return w;
  }

  // ---------------------------------------------------------------- engine
  function typeset(cfg, doc) {
    const P = cfg.page;
    const pageW = mm(P.w), pageH = mm(P.h);
    const textW0 = mm(P.w - P.marginInner - P.marginOuter);
    const topM = mm(P.marginTop), botM = mm(P.marginBottom);
    const textH = pageH - topM - botM;
    const gapC = mm(cfg.columns.gap);
    const colW = (textW0 - gapC) / 2;
    const T = cfg.type;
    const lh = pt(T.body.leading);
    const fnLh = pt(T.foot.leading);
    const orph = cfg.orphans || 2, wid = cfg.widows || 2;

    // style contexts ---------------------------------------------------------
    const ctxs = {
      body: { fam: T.body.family, size: pt(T.body.size), lead: T.body.leading },
      foot: { fam: T.foot.family, size: pt(T.foot.size) },
      h2: { fam: T.h2.family, size: pt(T.h2.size) },
      h3: { fam: T.h3.family, size: pt(T.h3.size) },
      abs: { fam: T.abstract.family, size: pt(T.abstract.size) },
    };
    const rel = { n: [400, 1], b: [700, 1], sm: [400, T.smallScale], smb: [700, T.smallScale], fnref: [700, T.fnrefScale], h: [700, 1] };
    function fontFor(ctxName, st) {
      const c = ctxs[ctxName];
      let [w, r] = rel[st];
      if (ctxName === 'h2' || ctxName === 'h3') { if (st === 'n') w = T[ctxName].weight; if (st === 'b') w = Math.max(w, T[ctxName].weight); }
      return `${w} ${(c.size * r).toFixed(3)}px "${c.fam}"`;
    }
    function spaceNat(ctxName) { return ctxs[ctxName].size * T.spaceEm; }
    function spaceGlyph(ctxName) { return textW(' ', fontFor(ctxName, 'n')); }

    // ------------------------------------------------------------ tokenising
    function styleOf(run, boldDefault) {
      const b = run.b || boldDefault;
      if (run.sm) return b ? 'smb' : 'sm';
      return b ? 'b' : 'n';
    }
    // returns [{segs:[{t,st}], w}] ; footnote refs become fnref segs
    function tokenize(runs, ctxName, fnMap, boldDefault) {
      const words = [];
      let cur = null;
      const push = () => { if (cur && cur.segs.length) words.push(cur); cur = null; };
      for (const r of runs) {
        if (r.fn !== undefined) {
          const fe = fnMap(r.fn);
          if (!fe) continue;
          if (!cur) cur = { segs: [] };
          cur.segs.push({ t: fe.label, st: 'fnref', fn: fe.key });
          cur.fn = (cur.fn || []).concat([fe.key]);
          continue;
        }
        const st = styleOf(r, boldDefault);
        const parts = r.t.split(/( )/);
        for (const pc of parts) {
          if (pc === ' ') { push(); continue; }
          if (!pc) continue;
          if (!cur) cur = { segs: [] };
          cur.segs.push({ t: pc, st });
        }
      }
      push();
      for (const w of words) w.w = w.segs.reduce((a, s) => a + textW(s.t, fontFor(ctxName, s.st)), 0);
      return words;
    }

    // ------------------------------------------------------------ line breaking (Knuth-Plass-ish DP)
    function breakDP(words, ctxName, widths, opts) {
      // widths: fn(lineIndex) -> available width ; opts: {lastNatural:true}
      const m = words.length;
      if (!m) return [];
      const S = spaceNat(ctxName), ST = ctxs[ctxName].size * T.stretchEm, SH = ctxs[ctxName].size * T.shrinkEm;
      const pref = [0]; for (const w of words) pref.push(pref[pref.length - 1] + w.w);
      const INF = 1e18;
      const memo = new Map();
      function cost(i, j, k) { // line = words[i..j)
        const L = widths(k);
        const n = j - i - 1;
        const Ww = pref[j] - pref[i];
        const last = j === m;
        if (last) {
          const nat = Ww + n * S;
          if (nat > L + 0.01) return nat > L + 0.5 && n === 0 ? 1e9 : INF; // overfull
          let c = 0;
          if (i > 0 && n === 0 && Ww < L * 0.22) c += 6e5;  // lonely short last word
          else if (i > 0 && n === 0) c += 3000;
          return c;
        }
        if (n === 0) return Ww > L ? 1e9 : 1.5e8;
        const gap = (L - Ww) / n;
        let r = gap >= S ? (gap - S) / ST : (gap - S) / SH;
        if (r < -1.001) return INF;
        if (r > 5) return INF;
        const bad = 100 * Math.pow(Math.abs(r), 3);
        return (1 + bad) * (1 + bad) + 10;
      }
      function f(i, k) {
        if (i === m) return [0, m];
        const key = i * 4 + k;
        const hit = memo.get(key);
        if (hit) return hit;
        let best = [INF, -1];
        const L = widths(k);
        for (let j = i + 1; j <= m; j++) {
          const n = j - i - 1;
          const minW = pref[j] - pref[i] + n * (S - SH);
          if (minW > L + 0.01 && j > i + 1) break;
          const c = cost(i, j, k);
          if (c >= INF) continue;
          const rest = f(j, Math.min(k + 1, 2))[0];
          if (rest >= INF) continue;
          const tot = c + rest;
          if (tot < best[0]) best = [tot, j];
        }
        if (best[1] < 0) { // forced: one word (overfull)
          const rest = f(i + 1, Math.min(k + 1, 2))[0];
          best = [1e12 + rest, i + 1];
        }
        memo.set(key, best);
        return best;
      }
      const out = [];
      let i = 0, k = 0;
      f(0, 0);
      while (i < m) {
        const j = f(i, k)[1];
        out.push({ from: i, to: j, k });
        i = j; k = Math.min(k + 1, 2);
      }
      return out;
    }

    // balanced centered text (headings)
    function breakBalanced(words, ctxName, L) {
      const m = words.length; if (!m) return [];
      const S = spaceNat(ctxName);
      const total = words.reduce((a, w) => a + w.w, 0) + (m - 1) * S;
      const k = Math.max(1, Math.ceil(total / L));
      const target = total / k;
      const pref = [0]; for (const w of words) pref.push(pref[pref.length - 1] + w.w);
      const INF = 1e18; const memo = new Map();
      function f(i, left) {
        if (i === m) return left === 0 ? [0, m] : [INF, -1];
        if (left === 0) return [INF, -1];
        const key = i * 64 + left; if (memo.has(key)) return memo.get(key);
        let best = [INF, -1];
        for (let j = i + 1; j <= m; j++) {
          const W = pref[j] - pref[i] + (j - i - 1) * S;
          if (W > L && j > i + 1) break;
          const c = Math.pow(W - target, 2) + (W > L ? 1e9 : 0);
          const r = f(j, left - 1)[0];
          if (c + r < best[0]) best = [c + r, j];
        }
        memo.set(key, best); return best;
      }
      let kk = k, res = f(0, kk);
      while (res[0] >= INF && kk < m) { kk++; memo.clear(); res = f(0, kk); }
      const out = []; let i = 0, left = kk;
      while (i < m) { const j = f(i, left)[1]; out.push({ from: i, to: j, k: 0 }); i = j; left--; }
      return out;
    }

    // ------------------------------------------------------------ article -> lines
    function layoutArticle(art, aIdx) {
      const lines = [];
      const fnReg = {};              // key -> entry
      let fnCount = 0;
      const fnMap = (id) => {
        const src = art.footnotes && art.footnotes[id];
        if (!src) return null;
        const key = aIdx + ':' + id;
        if (!fnReg[key]) {
          fnCount++;
          fnReg[key] = { key, n: fnCount, label: heb(fnCount), runs: src, lines: null };
        }
        return fnReg[key];
      };
      let prev = null; // previous block type
      let paraId = 0;
      for (const b of art.blocks) {
        const pid = ++paraId;
        if (b.t === 'p') {
          const words = tokenize(b.runs, 'body', fnMap, false);
          if (!words.length) continue;
          // lead-in: leading fully bold words
          let lead = 0;
          for (const w of words) { if (w.segs.every((s) => s.st === 'b' || s.st === 'smb' || s.st === 'fnref')) lead++; else break; }
          if (lead === words.length || lead > T.leadMaxWords) lead = 0;
          const S = spaceNat('body');
          let indent = 0;
          if (lead > 0) { for (let i = 0; i < lead; i++) indent += words[i].w; indent += lead * S; if (indent > colW * 0.45) indent = 0; }
          const widths = (k) => (k === 1 ? colW - indent : colW);
          const br = breakDP(words, 'body', widths, {});
          br.forEach((ln, idx) => {
            const lastL = idx === br.length - 1;
            const al = lastL && br.length > 1 ? cfg.lastLine : (lastL ? 'start' : 'justify');
            lines.push({
              ctx: 'body', words: words.slice(ln.from, ln.to), L: al === 'center' ? colW : widths(ln.k), indent: ln.k === 1 && al !== 'center' ? indent : 0,
              align: al,
              para: pid, idx, n: br.length, spaceBefore: idx === 0 ? (prev === null ? 0 : (prev === 'h3' ? 0 : 1)) : 0,
              keepNext: false, fn: [].concat(...words.slice(ln.from, ln.to).map((w) => w.fn || [])),
            });
          });
          prev = 'p';
        } else if (b.t === 'h2' || b.t === 'h3') {
          const ctxName = b.t;
          const words = tokenize(b.runs, ctxName, fnMap, true);
          if (!words.length) continue;
          const L = colW * (b.t === 'h2' ? 0.96 : 0.94);
          const br = breakBalanced(words, ctxName, L);
          br.forEach((ln, idx) => {
            lines.push({
              ctx: ctxName, words: words.slice(ln.from, ln.to), L, indent: 0, align: 'center', para: pid, idx, n: br.length,
              spaceBefore: idx === 0 ? (prev === null ? 0 : (b.t === 'h2' ? 2 : (prev === 'h2' ? 0 : 1))) : 0,
              keepNext: true, heading: true, fn: [].concat(...words.slice(ln.from, ln.to).map((w) => w.fn || [])),
            });
          });
          prev = b.t;
        }
      }
      // footnote lines
      const fw = textW0 - mm(cfg.footnotes.gutter);
      const fnEntries = Object.values(fnReg);
      for (const fe of fnEntries) {
        const words = tokenize(fe.runs, 'foot', () => null, false);
        const br = breakDP(words, 'foot', () => fw, {});
        fe.lines = br.map((ln, idx) => ({ words: words.slice(ln.from, ln.to), L: fw, last: idx === br.length - 1 }));
      }
      return { lines, fnReg };
    }

    // ------------------------------------------------------------ pagination
    const FN = cfg.footnotes;
    const fnTop = mm(FN.topGap), fnHeadH = fnLh * 1.15, fnHeadGap = mm(FN.headGap), fnItemGap = mm(FN.itemGap);
    function fnBlockH(entries) {
      if (!entries.length) return 0;
      let h = fnTop + fnHeadH + fnHeadGap;
      entries.forEach((e, i) => { h += (e.to - e.from) * fnLh + (i ? fnItemGap : 0); });
      return h;
    }

    function colUnits(arr) { let u = 0; arr.forEach((l, i) => { u += (i > 0 ? l.spaceBefore : 0) + 1; }); return u; }
    function allowedBreak(a, b) { // between line a and line b (b follows a)
      if (a.keepNext) return false;
      if (a.para === b.para) {
        const before = a.idx + 1, after = a.n - before;
        if (before < orph || after < wid) return false;
      }
      return true;
    }
    // split page lines into two columns; returns [col0,col1] or null.  mode: 'full' | 'balanced'
    function splitCols(lines, C, mode) {
      const n = lines.length;
      if (!n) return [[], []];
      if (mode === 'balanced') {
        let best = null;
        for (let b = 1; b <= n; b++) {
          if (b < n && !allowedBreak(lines[b - 1], lines[b])) continue;
          const c1 = lines.slice(0, b), c2 = lines.slice(b);
          const u1 = colUnits(c1), u2 = colUnits(c2);
          const mx = Math.max(u1, u2);
          const score = mx * 100 + (u2 > u1 ? 50 : 0) + Math.abs(u1 - u2);
          if (!best || score < best.score) best = { score, c1, c2, mx };
        }
        if (!best || best.mx > C) return null;
        return [best.c1, best.c2];
      }
      // full: fill col0 to C units
      let e = -1, u = 0;
      for (let i = 0; i < n; i++) { const nu = u + (i > 0 ? lines[i].spaceBefore : 0) + 1; if (nu > C) break; u = nu; e = i; }
      if (e === n - 1) return [lines, []];
      let b = e + 1; // lines in col0
      let found = -1;
      for (let t = b; t >= Math.max(1, b - 4); t--) { if (allowedBreak(lines[t - 1], lines[t])) { found = t; break; } }
      if (found > 0) b = found;
      const c1 = lines.slice(0, b), c2 = lines.slice(b);
      if (colUnits(c2) > C) return null;
      return [c1, c2];
    }

    function paginateArticle(L, banner, endOrnH) {
      const pages = [];
      const queue = L.lines.slice();
      let carry = []; // continued footnote entries [{key, from, to}]
      let first = true;
      let guard = 0;
      while (queue.length || carry.length) {
        if (++guard > 5000) throw new Error('pagination did not converge');
        const bannerH = first ? banner.h : 0;
        const page = { lines: [], entries: carry.map((e) => ({ ...e })), banner: first ? banner : null, first, endOrn: false };
        carry = [];
        const lineEntries = (lines) => { // footnote entries newly introduced by these lines
          const out = [];
          for (const l of lines) for (const k of l.fn) { if (!out.find((e) => e.key === k)) out.push({ key: k, from: 0, to: L.fnReg[k].lines.length }); }
          return out;
        };
        const capOf = (entries) => Math.floor((textH - bannerH - fnBlockH(entries) + 0.01) / lh);
        const entriesFor = (lines, splitLast) => {
          let es = page.carryEntries.concat(lineEntries(lines));
          if (splitLast && es.length) { const e = es[es.length - 1]; es = es.slice(0, -1).concat([{ ...e, to: splitLast }]); }
          return es;
        };
        page.carryEntries = page.entries;
        let closeSplit = null; // {key,k} when last footnote was split
        let progressed = false;
        while (queue.length) {
          const ln = queue[0];
          const trial = page.lines.concat([ln]);
          let es = entriesFor(trial, 0);
          let C = capOf(es);
          let cols = splitCols(trial, C, 'full');
          if (cols && C >= 1) { page.lines = trial; queue.shift(); progressed = true; continue; }
          // try splitting this line's last new footnote
          const newE = lineEntries(trial).filter((e) => !page.carryEntries.find((c) => c.key === e.key) && !lineEntries(page.lines).find((p) => p.key === e.key));
          if (newE.length) {
            const lastE = newE[newE.length - 1];
            const total = L.fnReg[lastE.key].lines.length;
            let ok = false;
            for (let k = total - 1; k >= 2; k--) {
              const es2 = entriesFor(trial, k);
              const C2 = capOf(es2);
              const cols2 = splitCols(trial, C2, 'full');
              if (cols2 && C2 >= 1) { closeSplit = { key: lastE.key, k, total }; page.lines = trial; queue.shift(); ok = true; progressed = true; break; }
            }
            if (ok) break;
          }
          if (!progressed && page.lines.length === 0) { // force one line so we always advance
            page.lines = [ln]; queue.shift(); progressed = true;
          }
          break;
        }
        // page break legality (orphans / widows / keep-next)
        if (window.__dbg) console.log('close page', pages.length+1, 'last:', page.lines.length && page.lines[page.lines.length-1].words.map(w=>w.segs.map(x=>x.t).join('')).join(' ').slice(0,30), '| heading', page.lines.length && page.lines[page.lines.length-1].heading, '| next:', queue[0] && queue[0].words.map(w=>w.segs.map(x=>x.t).join('')).join(' ').slice(0,30), 'closeSplit', !!closeSplit);
        if (queue.length && !closeSplit) {
          let pops = 0;
          while (page.lines.length > 8 && pops < 16 && !allowedBreak(page.lines[page.lines.length - 1], queue[0])) {
            queue.unshift(page.lines.pop()); pops++;
          }
        } else if (queue.length && closeSplit) {
          // keep as is
        }
        // final footnote entries
        let es = page.carryEntries.concat(lineEntries(page.lines));
        if (closeSplit && es.length && es[es.length - 1].key === closeSplit.key) {
          const e = es[es.length - 1];
          es = es.slice(0, -1).concat([{ ...e, to: closeSplit.k }]);
          carry = [{ key: closeSplit.key, from: closeSplit.k, to: closeSplit.total, cont: true }];
        }
        page.entries = es;
        page.fnH = fnBlockH(es);
        page.bannerH = bannerH;
        first = false;
        const isLast = queue.length === 0 && carry.length === 0;
        page.isLast = isLast;
        const C = Math.floor((textH - bannerH - page.fnH + 0.01) / lh);
        let cols;
        if (isLast) {
          const C2 = Math.floor((textH - bannerH - page.fnH - (endOrnH || 0) + 0.01) / lh);
          cols = splitCols(page.lines, C2, 'balanced');
          if (cols) page.endOrn = true; else cols = splitCols(page.lines, C, 'balanced');
        } else cols = splitCols(page.lines, C, 'full');
        if (!cols) cols = splitCols(page.lines, 999, 'full');
        page.cols = cols;
        page.C = C;
        pages.push(page);
      }
      return pages;
    }

    // ------------------------------------------------------------ DOM rendering
    const root = document.getElementById('pages');
    root.innerHTML = '';
    function wordsHTML(words, ctxName, gapPx) {
      const sg = spaceGlyph(ctxName);
      let html = '';
      words.forEach((w, i) => {
        if (i) html += ' ';
        for (const s of w.segs) html += `<span class="${s.st}">${esc(s.t)}</span>`;
      });
      return { html, ws: gapPx - sg };
    }
    function lineDiv(ln, x, y, ctxName) {
      const S = spaceNat(ctxName);
      const n = ln.words.length - 1;
      let gap = S;
      const Lw = ln.L;
      if (ln.align === 'justify' && n > 0) {
        const Ww = ln.words.reduce((a, w) => a + w.w, 0);
        gap = (Lw - Ww) / n;
      }
      const { html, ws } = wordsHTML(ln.words, ctxName, gap);
      const d = document.createElement('div');
      d.className = 'ln c-' + ctxName;
      const nat = ln.words.reduce((a, w) => a + w.w, 0) + n * gap;
      let left = x;                       // x = left coordinate of the available box (width Lw+indent)
      let wdt = Lw;
      if (ln.align === 'center') left = x + (Lw - nat) / 2 + ln.indent * 0; // indent is 0 for centered lines
      d.style.cssText = `left:${(ln.align === 'center' ? left : x).toFixed(2)}px;top:${y.toFixed(2)}px;width:${(ln.align === 'center' ? nat + 2 : Lw).toFixed(2)}px;height:${lh}px;line-height:${lh}px;word-spacing:${ws.toFixed(3)}px;`;
      d.innerHTML = html;
      return d;
    }

    // banner (title block) ----------------------------------------------------
    function ornSVG(kind) { return (cfg.ornaments && cfg.ornaments[kind]) || ''; }
    function bannerHTML(art) {
      let h = '<div class="banner">';
      if (art.basad) h += `<div class="basad">${esc(art.basad)}</div>`;
      if (art.label) h += `<div class="label">${esc(art.label)}</div>`;
      h += `<div class="ornament top">${ornSVG('top')}</div>`;
      h += `<div class="rule"></div><div class="title">${esc(art.title)}</div><div class="rule"></div>`;
      h += `<div class="ornament bot">${ornSVG('bottom')}</div>`;
      if (art.author) h += `<div class="author">${esc(art.author)}</div>`;
      if (art.abstract) h += `<div class="abstract">${esc(art.abstract)}</div>`;
      return h + '</div>';
    }
    const probe = document.createElement('div');
    probe.className = 'probe'; probe.style.cssText = `position:absolute;visibility:hidden;left:0;top:0;width:${textW0}px`;
    document.body.appendChild(probe);
    function measureBanner(art) {
      probe.innerHTML = bannerHTML(art);
      const h = probe.firstChild.getBoundingClientRect().height;
      return Math.ceil(h / lh) * lh + lh * (cfg.bannerBelow || 1);
    }

    // ------------------------------------------------------------ build all
    const allPages = [];
    let pageNo = doc.firstPageNumber || 1;
    const bookName = doc.book.name;
    const articles = doc.articles;
    const tocEntries = [];
    articles.forEach((art, aIdx) => {
      const L = layoutArticle(art, aIdx);
      const bh = art.noBanner ? 0 : measureBanner(art);
      const banner = { h: bh, html: art.noBanner ? '' : bannerHTML(art) };
      const endOrnH = lh * 3;
      const pages = paginateArticle(L, banner, endOrnH);
      pages.forEach((p, i) => { p.article = art; p.aIdx = aIdx; p.fnReg = L.fnReg; p.no = pageNo++; });
      tocEntries.push({ art, page: pages[0].no, pages: pages.length });
      allPages.push(...pages);
    });

    function headerHTML(p) {
      // Hebrew book: even pages are the right-hand page.  Page number sits on the outer edge, book name on the inner edge.
      const even = p.no % 2 === 0;
      const num = `<span class="hnum">${heb(p.no)}</span>`;
      const book = `<span class="hbook">${esc(bookName)}</span>`;
      const dot = '<span class="hdot">&#9679;</span>';
      const chap = `<span class="hchap">${esc(p.article.shortTitle || p.article.title)}</span>`;
      // visual order, left to right
      const html = even ? `${book}${dot}${chap}<span class="grow"></span>${num}` : `${num}<span class="grow"></span>${chap}${dot}${book}`;
      const ml = even ? mm(P.marginInner) : mm(P.marginOuter);
      return `<div class="header ${even ? 'even' : 'odd'}" style="left:${ml}px;width:${textW0}px">${html}</div>`;
    }

    allPages.forEach((p) => {
      const pg = document.createElement('div');
      pg.className = 'page';
      pg.style.width = pageW + 'px'; pg.style.height = pageH + 'px';
      const marginL = (p.no % 2 === 0) ? mm(P.marginInner) : mm(P.marginOuter);
      pg.innerHTML = headerHTML(p);
      const yText = topM;
      if (p.banner && p.banner.h) {
        const b = document.createElement('div');
        b.className = 'bannerWrap';
        b.style.cssText = `left:${marginL}px;top:${yText}px;width:${textW0}px;`;
        b.innerHTML = p.banner.html;
        pg.appendChild(b);
      }
      const yBody = yText + p.bannerH;
      const xCol = [marginL + colW + gapC, marginL]; // col0 = right column
      p.cols.forEach((col, ci) => {
        let y = yBody;
        col.forEach((ln, i) => {
          if (i > 0) y += ln.spaceBefore * lh;
          const ind = ln.indent || 0;
          const box = { ...ln };
          // lines with indent are right aligned: shrink from the right side
          const d = lineDiv(box, xCol[ci], y, ln.ctx);
          pg.appendChild(d);
          y += lh;
        });
        if (ci === 0) p._colEnd0 = y; else p._colEnd1 = y;
      });
      // footnotes
      if (p.entries.length) {
        let y = yText + textH - p.fnH + fnTop;
        const hd = document.createElement('div');
        hd.className = 'fnhead';
        hd.style.cssText = `left:${marginL}px;top:${y}px;width:${textW0}px;height:${fnHeadH}px;`;
        hd.innerHTML = `<span class="fnrule"></span><span class="fntitle">${esc(FN.title)}</span><span class="fnrule"></span>`;
        pg.appendChild(hd);
        y += fnHeadH + fnHeadGap;
        const gutter = mm(FN.gutter);
        p.entries.forEach((e, ei) => {
          if (ei) y += fnItemGap;
          const reg = p.fnReg[e.key];
          for (let li = e.from; li < e.to; li++) {
            const ln = reg.lines[li];
            const dl = lineDiv({ words: ln.words, L: ln.L, indent: 0, align: ln.last ? 'start' : 'justify' }, marginL, y, 'foot');
            dl.style.height = fnLh + 'px'; dl.style.lineHeight = fnLh + 'px';
            pg.appendChild(dl);
            if (li === e.from && !e.cont) {
              const mk = document.createElement('div');
              mk.className = 'fnmark';
              mk.style.cssText = `left:${marginL + ln.L}px;top:${y}px;width:${gutter}px;height:${fnLh}px;line-height:${fnLh}px;`;
              mk.textContent = reg.label + '.';
              pg.appendChild(mk);
            }
            y += fnLh;
          }
        });
      }
      // end ornament
      if (p.endOrn) {
        const colEnd = Math.max(p._colEnd0 || yBody, p._colEnd1 || yBody);
        const o = document.createElement('div');
        o.className = 'endorn';
        o.style.cssText = `left:${marginL}px;top:${colEnd + lh * 0.5}px;width:${textW0}px;`;
        o.innerHTML = ornSVG('end');
        pg.appendChild(o);
      }
      root.appendChild(pg);
    });
    return { pages: allPages.length, toc: tocEntries.map((t) => ({ title: t.art.title, page: t.page, pages: t.pages })) };
  }

  window.typeset = typeset;
  window.hebNum = heb;
})();
