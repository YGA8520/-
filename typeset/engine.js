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
    const L = [[400, 'ת'], [300, 'ש'], [200, 'ר'], [100, 'ק'], [90, 'צ'], [80, 'פ'], [70, 'ע'], [60, 'ס'], [50, 'נ'], [40, 'מ'], [30, 'ל'], [20, 'כ'], [10, 'י'], [9, 'ט'], [8, 'ח'], [7, 'ז'], [6, 'ו'], [5, 'ה'], [4, 'ד'], [3, 'ג'], [2, 'ב'], [1, 'א']];
    let s = '';
    while (n >= 100) { const [v, c] = L.find((x) => x[0] <= n && x[0] >= 100); s += c; n -= v; }
    if (n === 15) return s + 'טו';
    if (n === 16) return s + 'טז';
    for (const [v, c] of L) { if (v >= 100) continue; while (n >= v) { s += c; n -= v; } }
    return s;
  }
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  const nchars = (t) => t.replace(/[\u0591-\u05c7]/g, '').length;
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
    const rel = { n: [400, 1], b: [700, 1], sm: [400, T.smallScale], smb: [700, T.smallScale], fnref: [700, T.fnrefScale], h: [700, 1], ld: [700, (T.lead && T.lead.scale) || 1] };
    function fontFor(ctxName, st) {
      const c = ctxs[ctxName];
      if (st === 'ld') return `700 ${(c.size * rel.ld[1]).toFixed(3)}px "${T.lead.family}"`;
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
      // widths: fn(lineIndex) -> available width.  Stretch/shrink is shared between the word gaps and a slight letter-spacing
      // (same rule as in lineDiv), so the optimiser knows how much a line can really give.
      const m = words.length;
      if (!m) return [];
      const em = ctxs[ctxName].size;
      const S = spaceNat(ctxName), ST = em * T.stretchEm, SH = em * T.shrinkEm;
      const TR = cfg.tracking || { share: 0.5, minEm: -0.02, maxEm: 0.03 };
      const pref = [0], prefC = [0];
      for (const w of words) { pref.push(pref[pref.length - 1] + w.w); prefC.push(prefC[prefC.length - 1] + w.segs.reduce((a, s) => a + nchars(s.t), 0)); }
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
        const letters = prefC[j] - prefC[i];
        const extra = L - Ww - n * S;
        const trk = Math.max(letters * TR.minEm * em, Math.min(letters * TR.maxEm * em, extra * TR.share));
        const rest = extra - trk;                                  // what the word gaps must still give
        let r = rest >= 0 ? rest / (n * ST) : rest / (n * SH);
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
          const letters = prefC[j] - prefC[i];
          const minW = pref[j] - pref[i] + n * (S - SH) + letters * TR.minEm * em;
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
          // lead-in: the first word of EVERY paragraph (plus an enumerator such as "א׳." and its following word)
          let lead = 0;
          for (const w of words) { if (w.segs.every((x) => x.st === 'b' || x.st === 'smb' || x.st === 'fnref')) lead++; else break; }
          if (lead > T.leadMaxWords) lead = 1;
          if (lead === 0) lead = 1;
          const plain = (w) => w.segs.map((x) => x.t).join('');
          if (lead === 1 && words.length > 1 && /^(?:\(?[א-ת]{1,3}[׳'.):]+|\d{1,3}[.)])$/.test(plain(words[0]))) lead = 2;
          if (lead > words.length) lead = words.length;
          const S = spaceNat('body');
          const restyle = (w) => { for (const x of w.segs) if (x.st === 'n' || x.st === 'b') x.st = 'ld'; w.w = w.segs.reduce((a, x) => a + textW(x.t, fontFor('body', x.st)), 0); };
          const tryLead = (n) => { let ind = 0; for (let i = 0; i < n; i++) ind += words[i].w; return ind + n * S; };
          for (let i = 0; i < lead; i++) restyle(words[i]);
          let indent = tryLead(lead);
          if (indent > colW * 0.42 && lead > 1) { lead = 1; indent = tryLead(1); }
          if (indent > colW * 0.42) indent = 0;
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
        } else if (b.t === 'tbl') {
          const t = makeTable(b);
          lines.push({ tbl: true, html: t.html, h: t.h, para: pid, idx: 0, n: 1, spaceBefore: 0, keepNext: false, fn: [] });
          prev = 'tbl';
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
              keepNext: idx === br.length - 1, heading: true, fn: [].concat(...words.slice(ln.from, ln.to).map((w) => w.fn || [])),
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
    const fnTop = mm(FN.topGap), fnHeadH = mm(FN.headH || 4.8), fnHeadGap = mm(FN.headGap), fnItemGap = mm(FN.itemGap);
    const ORN = cfg.ornaments || {};
    const oimg = (name, wmm, cls, extra) => { const o = ORN[name]; if (!o) return ''; const h = wmm * o.h / o.w; return `<img class="orn ${cls || ''}" src="${o.src}" style="width:${wmm}mm;height:${h.toFixed(3)}mm;${extra || ''}">`; };
    function fnBlockH(entries) {
      if (!entries.length) return 0;
      let h = fnTop + fnHeadH + fnHeadGap;
      entries.forEach((e, i) => { h += (e.to - e.from) * fnLh + (i ? fnItemGap : 0); });
      return h;
    }

    const probe = document.createElement('div');
    probe.className = 'probe'; probe.style.cssText = `position:absolute;visibility:hidden;left:0;top:0;width:${textW0}px`;
    document.body.appendChild(probe);

    // tables (full-width bands) ----------------------------------------------
    function runsHTML(runs) {
      return runs.map((r) => (r.fn !== undefined ? '' : `<span class="${r.b ? (r.sm ? 'smb' : 'b') : (r.sm ? 'sm' : 'n')}">${esc(r.t)}</span>`)).join('');
    }
    function makeTable(b) {
      let h = '<table class="bt">';
      b.rows.forEach((row, ri) => {
        h += '<tr>';
        row.forEach((cell) => { h += (ri === 0 ? '<th>' : '<td>') + runsHTML(cell) + (ri === 0 ? '</th>' : '</td>'); });
        h += '</tr>';
      });
      h += '</table>';
      const html = `<div class="tblwrap" style="width:${(textW0 * 0.94).toFixed(1)}px">${h}</div>`;
      probe.innerHTML = html;
      const hh = probe.firstChild.getBoundingClientRect().height;
      return { html, h: Math.ceil((hh + lh * 0.9) / lh) * lh };
    }

    function colUnits(arr) { let u = 0; arr.forEach((l, i) => { u += (i > 0 ? l.spaceBefore : 0) + 1; }); return u; }
    function allowedBreak(a, b, relax) { // between line a and line b (b follows a); relax = accept single-line widows/orphans
      if (a.tbl || b.tbl) return true;
      if (a.keepNext) return false;
      if (a.para === b.para) {
        const before = a.idx + 1, after = a.n - before;
        if (before < (relax ? 1 : orph) || after < (relax ? 1 : wid)) return false;
      }
      return true;
    }
    // split lines of one band into two columns; returns [col0,col1] or null.  mode: 'full' | 'balanced'
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
      let e = -1, u = 0;
      for (let i = 0; i < n; i++) { const nu = u + (i > 0 ? lines[i].spaceBefore : 0) + 1; if (nu > C) break; u = nu; e = i; }
      if (e === n - 1) return [lines, []];
      let b = e + 1;
      // choose the break that wastes the least space: every line pulled back to column 2 costs 1, a single-line widow/orphan costs 0.7
      let bestT = -1, bestCost = 1e9;
      for (let t = b; t >= Math.max(1, b - 3); t--) {
        if (!allowedBreak(lines[t - 1], lines[t], true)) continue;           // never strand a heading
        const cst = (b - t) + (allowedBreak(lines[t - 1], lines[t], false) ? 0 : 0.7);
        if (cst < bestCost) { bestCost = cst; bestT = t; }
      }
      if (bestT > 0) b = bestT;
      const c1 = lines.slice(0, b), c2 = lines.slice(b);
      if (colUnits(c2) > C) return null;
      return [c1, c2];
    }

    function paginateArticle(L, banner, endOrnH) {
      const pages = [];
      const queue = L.lines.slice();
      let carry = [];
      let first = true;
      let guard = 0;
      while (queue.length || carry.length) {
        if (++guard > 6000) throw new Error('pagination did not converge');
        const bannerH = first ? banner.h : 0;
        const page = { bands: [], open: [], usedTop: bannerH, banner: first ? banner : null, first, endOrn: false, carryEntries: carry.map((e) => ({ ...e })) };
        carry = [];
        const flat = (open) => { const a = []; for (const b of page.bands) if (b.type === 'cols') a.push(...b.lines); a.push(...open); return a; };
        const lineEntries = (lines) => {
          const out = [];
          for (const l of lines) for (const k of l.fn) { if (!out.find((e) => e.key === k)) out.push({ key: k, from: 0, to: L.fnReg[k].lines.length }); }
          return out;
        };
        const entriesFor = (open, splitLast) => {
          let es = page.carryEntries.concat(lineEntries(flat(open)));
          if (splitLast && es.length) { const e = es[es.length - 1]; es = es.slice(0, -1).concat([{ ...e, to: splitLast }]); }
          return es;
        };
        const capOf = (entries) => Math.floor((textH - page.usedTop - fnBlockH(entries) + 0.01) / lh);
        let closeSplit = null;
        let progressed = false;
        const deferred = [];
        while (queue.length) {
          const ln = queue[0];
          if (ln.tbl) {
            const es0 = entriesFor(page.open, 0);
            const rem0 = textH - page.usedTop - fnBlockH(es0);
            let before = null, hBefore = 0;
            if (page.open.length) {
              before = splitCols(page.open, Math.floor(rem0 / lh), 'balanced');
              if (!before) break;
              hBefore = Math.max(colUnits(before[0]), colUnits(before[1])) * lh;
            }
            const empty = page.bands.length === 0 && page.open.length === 0;
            if (ln.h <= rem0 - hBefore + 0.5 || empty) {
              if (page.open.length) { page.bands.push({ type: 'cols', cols: before, lines: page.open, h: hBefore }); page.usedTop += hBefore; page.open = []; }
              page.bands.push({ type: 'tbl', item: ln, h: ln.h }); page.usedTop += ln.h; queue.shift(); progressed = true; continue;
            }
            // does not fit: float it to the top of the next page and let the following text fill this page
            if (queue.length > 1 && !queue[1].tbl && (textH - page.usedTop) > ln.h * 0.35) { deferred.push(queue.shift()); continue; }
            break;
          }
          const trial = page.open.concat([ln]);
          const es = entriesFor(trial, 0);
          const C = capOf(es);
          if (C >= 1 && splitCols(trial, C, 'full')) { page.open = trial; queue.shift(); progressed = true; continue; }
          const prevKeys = lineEntries(flat(page.open)).map((e) => e.key);
          const newE = lineEntries(flat(trial)).filter((e) => !page.carryEntries.find((c) => c.key === e.key) && !prevKeys.includes(e.key));
          if (newE.length) {
            const lastE = newE[newE.length - 1];
            const total = L.fnReg[lastE.key].lines.length;
            let ok = false;
            for (let k = total - 1; k >= 2; k--) {
              const C2 = capOf(entriesFor(trial, k));
              if (C2 >= 1 && splitCols(trial, C2, 'full')) { closeSplit = { key: lastE.key, k, total }; page.open = trial; queue.shift(); ok = true; progressed = true; break; }
            }
            if (ok) break;
          }
          if (!progressed && page.open.length === 0 && page.bands.length === 0) { page.open = [ln]; queue.shift(); progressed = true; }
          break;
        }
        if (queue.length && !closeSplit) {
          let p = -1, bestCost = 1e9;
          for (let q = 0; q <= 3; q++) {
            const n = page.open.length - q;
            if (n <= 8) break;
            const nxt = q ? page.open[n] : queue[0];
            if (!allowedBreak(page.open[n - 1], nxt, true)) continue;
            const cst = q + (allowedBreak(page.open[n - 1], nxt, false) ? 0 : 0.7);
            if (cst < bestCost) { bestCost = cst; p = q; }
          }
          if (p < 0) {                       // e.g. a long heading chain: pull back as far as needed
            for (let q = 4; q <= 16; q++) {
              const n = page.open.length - q;
              if (n <= 8) break;
              if (allowedBreak(page.open[n - 1], page.open[n], false)) { p = q; break; }
            }
          }
          if (p < 0) p = 0;
          for (let i = 0; i < p; i++) queue.unshift(page.open.pop());
        }
        if (deferred.length) queue.unshift(...deferred);
        let es = page.carryEntries.concat(lineEntries(flat(page.open)));
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
        const C = Math.floor((textH - page.usedTop - page.fnH + 0.01) / lh);
        let cols;
        if (isLast) {
          const C2 = Math.floor((textH - page.usedTop - page.fnH - (endOrnH || 0) + 0.01) / lh);
          cols = splitCols(page.open, C2, 'balanced');
          if (cols) page.endOrn = true; else cols = splitCols(page.open, C, 'balanced');
        } else cols = splitCols(page.open, C, 'full');
        if (!cols) cols = splitCols(page.open, 999, 'full');
        page.bands.push({ type: 'cols', cols, lines: page.open, last: true });
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
    const STATS = { pages: [], loose: [] };
    let curPage = null;
    const TRK = cfg.tracking || { share: 0.5, minEm: -0.02, maxEm: 0.03 };
    function lineDiv(ln, x, y, ctxName) {
      const S = spaceNat(ctxName);
      const n = ln.words.length - 1;
      const Lw = ln.L;
      const Ww = ln.words.reduce((a, w) => a + w.w, 0);
      let gap = S, ls = 0;
      if (ln.align === 'justify' && n > 0) {
        // part of the stretch/shrink is absorbed by a very slight letter-spacing so that word gaps vary less from line to line
        const extra = Lw - Ww - n * S;
        const letters = ln.words.reduce((a, w) => a + w.segs.reduce((b, s) => b + nchars(s.t), 0), 0);
        const em = ctxs[ctxName].size;
        const lsTotal = Math.max(letters * TRK.minEm * em, Math.min(letters * TRK.maxEm * em, extra * TRK.share));
        ls = letters ? lsTotal / letters : 0;
        gap = (Lw - Ww - ls * letters) / n;
        const ratio = gap / S;
        STATS.hist = STATS.hist || {};
        const bin = Math.min(12, Math.max(0, Math.round(gap / em * 20)));   // bins of 0.05em
        STATS.hist[bin] = (STATS.hist[bin] || 0) + 1;
        if (curPage !== null && (ratio > 1.9 || ratio < 0.72)) STATS.loose.push({ page: curPage, ratio: +ratio.toFixed(2), ctx: ctxName, text: ln.words.map((w) => w.segs.map((s) => s.t).join('')).join(' ').slice(0, 50) });
      }
      const { html, ws } = wordsHTML(ln.words, ctxName, gap);
      const d = document.createElement('div');
      d.className = 'ln c-' + ctxName;
      const nat = Ww + n * gap;
      const left = ln.align === 'center' ? x + (Lw - nat) / 2 : x;
      d.style.cssText = `left:${left.toFixed(2)}px;top:${y.toFixed(2)}px;width:${(ln.align === 'center' ? nat + 2 : Lw).toFixed(2)}px;height:${lh}px;line-height:${lh}px;word-spacing:${(ws - ls).toFixed(3)}px;` + (ls ? `letter-spacing:${ls.toFixed(3)}px;` : '');
      d.innerHTML = html;
      return d;
    }

    // ------------------------------------------------------------ frame ornament (title / divider), assembled from 3 slices
    const capL = ORN['frame-capL'], capR = ORN['frame-capR'], capM = ORN['frame-mid'];
    const TF = cfg.titleFrame || { size: 16.5, lead: 22, padV: 3.0, padH: 4.5, family: 'Frank Ruhl Libre', weight: 800, minW: 62 };
    const DV = cfg.dividerFrame || { size: 30, lead: 38, padV: 5.5, padH: 8, family: 'Frank Ruhl Libre', weight: 800, minW: 80 };
    const boxCache = new Map();
    function frameBox(text, P2, maxW) {
      const key = text + '|' + P2.size;
      if (boxCache.has(key)) return boxCache.get(key);
      ctxs.ttl = { fam: P2.family, size: pt(P2.size) };
      const font = `${P2.weight} ${pt(P2.size)}px "${P2.family}"`;
      const words = text.split(/\s+/).filter(Boolean).map((w) => ({ segs: [{ t: w, st: 'n' }], w: textW(w, font) }));
      const lineH = pt(P2.lead), padV = mm(P2.padV), padH = mm(P2.padH);
      let limit = maxW - mm(18), res = null;
      for (let it = 0; it < 6; it++) {
        const br = breakBalanced(words, 'ttl', limit);
        const lines = br.map((b) => words.slice(b.from, b.to).map((w) => w.segs[0].t).join(' '));
        const lw = lines.map((l) => textW(l, font));
        const H = lines.length * lineH + 2 * padV;
        const cw = H * capL.w / capL.h, crw = H * capR.w / capR.h;
        const W = Math.max(mm(P2.minW), Math.max(...lw) + 2 * padH + cw + crw);
        res = { lines, H, W, cw, crw, lineH };
        if (W <= maxW + 0.5) break;
        limit -= (W - maxW) + 4;
      }
      res.wmm = res.W / MM; res.hmm = res.H / MM;
      boxCache.set(key, res);
      return res;
    }
    function frameHTML(b, cls) {
      return `<div class="tframe ${cls || ''}" style="width:${b.W.toFixed(2)}px;height:${b.H.toFixed(2)}px">` +
        `<div class="fcap" style="left:0;width:${b.cw.toFixed(2)}px;background-image:url(${capL.src})"></div>` +
        `<div class="fmid" style="left:${b.cw.toFixed(2)}px;width:${(b.W - b.cw - b.crw).toFixed(2)}px;background-image:url(${capM.src})"></div>` +
        `<div class="fcap" style="right:0;width:${b.crw.toFixed(2)}px;background-image:url(${capR.src})"></div>` +
        `<div class="ftext" style="line-height:${b.lineH}px">${b.lines.map((l) => `<div class="fl" style="height:${b.lineH}px">${esc(l)}</div>`).join('')}</div></div>`;
    }

    // banner (title block) ----------------------------------------------------
    function bannerHTML(art) {
      let h = '<div class="banner">';
      if (art.basad) h += `<div class="basad">${esc(art.basad)}</div>`;
      const b = frameBox(art.title, TF, textW0 * 0.96);
      h += `<div class="tbox">${frameHTML(b, 'ttl')}</div>`;
      if (art.subtitle) h += `<div class="subtitle">${esc(art.subtitle)}</div>`;
      if (art.author) h += `<div class="author">${esc(art.author)}</div>`;
      if (art.abstract) h += `<div class="abstract">${esc(art.abstract)}</div>`;
      return h + '</div>';
    }
    function measureBanner(art) {
      probe.innerHTML = bannerHTML(art);
      const h = probe.firstChild.getBoundingClientRect().height;
      return Math.ceil(h / lh) * lh + lh * (cfg.bannerBelow || 1);
    }

    // ------------------------------------------------------------ lay out all articles
    const bookName = doc.book.name;
    const articles = doc.articles;
    const artPages = [];
    const titleBoxes = {}, dividerBoxes = {};
    articles.forEach((art, aIdx) => {
      const L = layoutArticle(art, aIdx);
      const bh = art.noBanner ? 0 : measureBanner(art);
      const banner = { h: bh, html: art.noBanner ? '' : bannerHTML(art) };
      const tb = frameBox(art.title, TF, textW0 * 0.96);
      titleBoxes[aIdx] = { wmm: tb.wmm, hmm: tb.hmm, lines: tb.lines, lineH: TF.lead };
      const pages = paginateArticle(L, banner, lh * 3);
      pages.forEach((p) => { p.article = art; p.aIdx = aIdx; p.fnReg = L.fnReg; });
      artPages.push(pages);
      if (art.divider && !dividerBoxes[art.divider]) {
        const db = frameBox(art.divider, DV, textW0 * 0.9);
        dividerBoxes[art.divider] = { wmm: db.wmm, hmm: db.hmm, lines: db.lines, lineH: DV.lead };
      }
    });

    // sequence of pages: divider pages come where the siman changes
    const seq = [];
    articles.forEach((art, ai) => { if (art.divider) seq.push({ kind: 'div', label: art.divider, ai }); seq.push({ kind: 'art', ai }); });

    // ------------------------------------------------------------ front matter: table of contents
    function tocRows(pageOf, divOf) {
      const rows = [];
      articles.forEach((art, i) => {
        if (art.divider) {
          const pn = divOf ? heb(divOf(i)) : 'תשצט';
          rows.push({ kind: 'group', html: `<div class="toc-group"><span>${esc(art.divider)}</span><span class="gl"></span><span class="gpn">${pn}</span></div>` });
        }
        const pn = pageOf ? heb(pageOf(i)) : 'תשצט';
        rows.push({ kind: 'entry', art: i, html: `<div class="toc-entry"><div class="t1"><span class="tt">${esc(art.title)}</span><span class="dots"></span><span class="pn">${pn}</span></div>${art.author ? `<div class="t2">${esc(art.author)}</div>` : ''}</div>` });
      });
      return rows;
    }
    const tocTitleHTML = `<div class="toc-title"><div class="orn-row top">${oimg('flourish-wide-2', 30, '', '')}</div><div class="tt">${esc((doc.toc && doc.toc.title) || 'תוכן עניינים')}</div><div class="orn-row bot">${oimg('divider-fleuron', 40, '', '')}</div></div>`;
    function paginateToc(rows) {
      const hs = rows.map((r) => { probe.innerHTML = r.html; return probe.firstChild.getBoundingClientRect().height; });
      probe.innerHTML = tocTitleHTML; const titleH = probe.firstChild.getBoundingClientRect().height + mm(6);
      const fill = (avail1, availN) => {
        const pages = []; let cur = [], used = titleH, avail = avail1;
        rows.forEach((r, i) => {
          const need = hs[i] + (r.kind === 'group' && rows[i + 1] ? hs[i + 1] : 0);
          if (used + need > avail && cur.length) { pages.push(cur); cur = []; used = 0; avail = availN; }
          cur.push(r); used += hs[i];
        });
        if (cur.length) pages.push(cur);
        return pages;
      };
      const full = textH - mm(4);
      let pages = fill(full, full);
      const n = pages.length;
      if (n > 1) {                                   // spread the rows evenly over the same number of pages
        const total = hs.reduce((a, b) => a + b, 0) + titleH;
        for (let k = 1.02; k < 1.6; k += 0.03) {
          const target = Math.min(full, (total / n) * k);
          const p2 = fill(target, target);
          if (p2.length <= n) { pages = p2; break; }
        }
      }
      return pages;
    }
    const tocPlaceholder = paginateToc(tocRows(null, null));
    const nToc = tocPlaceholder.length;
    let pageNo = (doc.firstPageNumber || 1) + nToc;       // ToC pages are counted in the numbering, the cover is not
    const startNo = [], divNo = [];
    seq.forEach((it) => {
      if (it.kind === 'div') { it.no = pageNo; divNo[it.ai] = pageNo++; }
      else { startNo[it.ai] = pageNo; artPages[it.ai].forEach((p) => { p.no = pageNo++; }); }
    });
    const tocPages = paginateToc(tocRows((i) => startNo[i], (i) => divNo[i]));
    if (tocPages.length !== nToc) console.log('warning: toc page count changed');

    // ------------------------------------------------------------ DOM: pages
    function newPage() {
      const pg = document.createElement('div');
      pg.className = 'page';
      pg.style.width = pageW + 'px'; pg.style.height = pageH + 'px';
      return pg;
    }
    if (!doc.noCover) {                      // placeholder cover until the real one is supplied
      const pg = newPage();
      pg.classList.add('cover');
      pg.innerHTML = `<div class="cover-in">${oimg('flourish-wide-1', 70, '', '')}<div class="cv-title">${esc(bookName)}</div>${doc.book.subtitle ? `<div class="cv-sub">${esc(doc.book.subtitle)}</div>` : ''}${oimg('flourish-wide-1', 70, '', 'transform:scaleY(-1);')}</div>`;
      root.appendChild(pg);
    }
    tocPages.forEach((rows, ti) => {
      const pg = newPage();
      const no = (doc.firstPageNumber || 1) + ti;
      const ml = (no % 2 === 0) ? mm(P.marginInner) : mm(P.marginOuter);
      pg.innerHTML = `<div class="tocwrap" style="left:${ml}px;top:${topM - mm(2)}px;width:${textW0}px">${ti === 0 ? tocTitleHTML : ''}${rows.map((r) => r.html).join('')}</div>`;
      root.appendChild(pg);
    });

    const hdrCache = new Map();
    function headerTitle(art) {
      const full = art.shortTitle || art.title;
      if (hdrCache.has(full)) return hdrCache.get(full);
      const bookW = textW(bookName, '800 ' + pt(15) + 'px "' + (cfg.fonts || {}).display + '"');
      const room = textW0 - bookW - mm(13) - mm(12);            // minus page number, bullet and gaps
      const f = '400 ' + pt(10) + 'px "' + (cfg.fonts || {}).lead + '"';
      let words = full.split(/\s+/), out = full;
      if (textW(full, f) > room) {
        while (words.length > 1 && textW(words.join(' ') + '…', f) > room) words.pop();
        out = words.join(' ').replace(/[\s,.:;\-–]+$/, '') + '…';
      }
      hdrCache.set(full, out);
      return out;
    }
    function headerHTML(p) {
      // Hebrew book: even pages are the right-hand page.  Page number sits on the outer edge, book name on the inner edge.
      const even = p.no % 2 === 0;
      const num = `<span class="hnum">${heb(p.no)}</span>`;
      const book = `<span class="hbook">${esc(bookName)}</span>`;
      const dot = '<span class="hdot">&#9679;</span>';
      const chap = `<span class="hchap">${esc(headerTitle(p.article))}</span>`;
      const html = even ? `${book}${dot}${chap}<span class="grow"></span>${num}` : `${num}<span class="grow"></span>${chap}${dot}${book}`;
      const ml = even ? mm(P.marginInner) : mm(P.marginOuter);
      const hr = ORN['header-rule'];
      const rule = hr ? `<img class="orn hrule" src="${hr.src}" style="left:${ml}px;top:${mm((cfg.header && cfg.header.ruleTop) || 25.2)}px;width:${textW0}px;height:${(textW0 * hr.h / hr.w).toFixed(2)}px">` : '';
      return `<div class="header ${even ? 'even' : 'odd'}" style="left:${ml}px;width:${textW0}px">${html}</div>${rule}`;
    }

    // vertical justification of one column: stretch the paragraph gaps (then, slightly, the leading) so that the column ends at `Ht`
    const VJ = Object.assign({ softGap: 0.35, softLead: 0.035, maxGap: 0.9, maxLead: 0.06 }, cfg.verticalJustify || {});
    function colPositions(col, y0, Ht) {
      const n = col.length;
      let slack = Ht - colUnits(col) * lh;
      let gapExtra = 0, leadExtra = 0;
      if (slack > 0.5 && n > 1) {
        const wsum = col.reduce((a, l, i) => a + (i > 0 ? l.spaceBefore : 0), 0);
        const sg = VJ.softGap * lh, sl = VJ.softLead * lh, hg = VJ.maxGap * lh, hl = VJ.maxLead * lh;
        const capG1 = sg * wsum, capL1 = sl * (n - 1);
        if (slack <= capG1 + capL1) {                       // soft: spread over paragraph gaps and leading together
          const f = slack / (capG1 + capL1);
          gapExtra = sg * f; leadExtra = sl * f; slack = 0;
        } else {                                            // hard: soft limits first, then gaps, then leading up to their maxima
          gapExtra = sg; leadExtra = sl; slack -= capG1 + capL1;
          if (wsum > 0) { const add = Math.min(slack / wsum, hg - sg); gapExtra += add; slack -= add * wsum; }
          if (slack > 0.5) { const add = Math.min(slack / (n - 1), hl - sl); leadExtra += add; slack -= add * (n - 1); }
        }
      }
      const out = []; let y = y0, end = y0;
      col.forEach((ln, i) => {
        if (i > 0) y += ln.spaceBefore * lh + gapExtra * ln.spaceBefore + leadExtra;
        out.push({ ln, y }); y += lh; end = y;
      });
      return { out, end, gapExtra, leadExtra, left: slack };
    }

    seq.forEach((it) => {
      if (it.kind === 'div') {
        const pg = newPage();
        const b = dividerBoxes[it.label];
        const fb = frameBox(it.label, DV, textW0 * 0.9);
        pg.innerHTML = `<div class="divwrap" style="top:${(pageH * 0.31).toFixed(1)}px">${oimg('flourish-wide-2', 46, '', '')}<div class="tbox big">${frameHTML(fb, 'dv')}</div>${oimg('flourish-wide-2', 46, '', 'transform:scaleY(-1);')}</div>`;
        root.appendChild(pg);
        return;
      }
      artPages[it.ai].forEach((p) => {
        const pg = newPage();
        const marginL = (p.no % 2 === 0) ? mm(P.marginInner) : mm(P.marginOuter);
        pg.innerHTML = headerHTML(p);
        const yText = topM;
        if (p.banner && p.banner.h) {
          const bw = document.createElement('div');
          bw.className = 'bannerWrap';
          bw.style.cssText = `left:${marginL}px;top:${yText}px;width:${textW0}px;`;
          bw.innerHTML = p.banner.html;
          pg.appendChild(bw);
        }
        let y = yText + p.bannerH;
        const xCol = [marginL + colW + gapC, marginL]; // col0 = right column
        const bodyBottom = yText + textH - p.fnH;      // columns of a full page end exactly here
        for (const band of p.bands) {
          if (band.type === 'tbl') {
            const d = document.createElement('div');
            d.className = 'tblband';
            d.style.cssText = `left:${marginL + textW0 * 0.03}px;top:${(y + lh * 0.45).toFixed(2)}px;width:${(textW0 * 0.94).toFixed(1)}px;`;
            d.innerHTML = band.item.html;
            pg.appendChild(d);
            y += band.h;
            continue;
          }
          let balanced = !band.last || p.isLast;
          if (!balanced) {
            // a column that cannot be filled even with the maximal stretch (e.g. the next line brought a long footnote):
            // better two equal columns with a little white space at the bottom than one ragged column
            const left = band.cols.map((col) => colPositions(col, y, bodyBottom - y).left);
            if (Math.max(...left) > lh * 1.0) {
              const re = splitCols(band.lines, 999, 'balanced');
              if (re) { band.cols = re; balanced = true; }
            }
          }
          const natural = Math.max(colUnits(band.cols[0]), colUnits(band.cols[1])) * lh;
          const Ht = balanced ? natural : (bodyBottom - y);
          let endY = y;
          curPage = p.no;
          const st = { page: p.no, art: p.aIdx, mode: balanced ? 'bal' : 'full', cols: [] };
          band.cols.forEach((col, ci) => {
            const { out, end, gapExtra, leadExtra, left } = colPositions(col, y, Ht);
            out.forEach(({ ln, y: yy }) => pg.appendChild(lineDiv(ln, xCol[ci], yy, ln.ctx)));
            endY = Math.max(endY, end);
            st.cols.push({ n: col.length, units: colUnits(col), gap: +(gapExtra / lh).toFixed(2), lead: +(leadExtra / lh).toFixed(3), left: +(Math.max(0, left) / lh).toFixed(2), end: +((end - y) / lh).toFixed(2) });
          });
          STATS.pages.push(st);
          y = balanced ? y + natural : bodyBottom;
          p._endY = y;
        }
        // footnotes
        if (p.entries.length) {
          let fy = yText + textH - p.fnH + fnTop;
          const hd = document.createElement('div');
          hd.className = 'fnhead';
          hd.style.cssText = `left:${marginL}px;top:${fy}px;width:${textW0}px;height:${fnHeadH}px;`;
          const tsize = FN.titleSize || 10.5;
          const titleW = textW(FN.title, `700 ${pt(tsize)}px "${FN.titleFamily}"`);
          const gapmm = FN.titleGap || 4;
          const sw = Math.min(FN.sideMax || 60, (textW0 - titleW - mm(2 * gapmm)) / 2 / MM);
          const ln = (flip) => `<img class="orn fnside" src="${ORN['fn-lines'].src}" style="width:${sw.toFixed(2)}mm;height:${FN.linesH || 1.9}mm">`;
          hd.innerHTML = `${ln()}<span class="fntitle" style="font-size:${tsize}pt">${esc(FN.title)}</span>${ln()}`;
          hd.style.justifyContent = 'center'; hd.style.gap = gapmm + 'mm';
          pg.appendChild(hd);
          fy += fnHeadH + fnHeadGap;
          const gutter = mm(FN.gutter);
          p.entries.forEach((e, ei) => {
            if (ei) fy += fnItemGap;
            const reg = p.fnReg[e.key];
            for (let li = e.from; li < e.to; li++) {
              const l2 = reg.lines[li];
              const dl = lineDiv({ words: l2.words, L: l2.L, indent: 0, align: l2.last ? 'start' : 'justify' }, marginL, fy, 'foot');
              dl.style.height = fnLh + 'px'; dl.style.lineHeight = fnLh + 'px';
              pg.appendChild(dl);
              if (li === e.from && !e.cont) {
                const mk = document.createElement('div');
                mk.className = 'fnmark';
                mk.style.cssText = `left:${marginL + l2.L}px;top:${fy}px;width:${gutter}px;height:${fnLh}px;line-height:${fnLh}px;`;
                mk.textContent = reg.label + '.';
                pg.appendChild(mk);
              }
              fy += fnLh;
            }
          });
        }
        if (p.endOrn) {      // end-of-article ornament, turned upside down so that it points down
          const o = document.createElement('div');
          o.className = 'endorn';
          o.style.cssText = `left:${marginL}px;top:${(p._endY || y) + lh * 0.5}px;width:${textW0}px;`;
          o.innerHTML = oimg((cfg.endOrnament && cfg.endOrnament.name) || 'fleuron-small', (cfg.endOrnament && cfg.endOrnament.w) || 18, '', 'transform:scaleY(-1);');
          pg.appendChild(o);
        }
        root.appendChild(pg);
      });
    });
    curPage = null;
    return { stats: STATS, pages: root.children.length, toc: articles.map((a, i) => ({ title: a.title, page: startNo[i], pages: artPages[i].length })), tocPages: nToc, titleBoxes, dividerBoxes, dividerPages: divNo, headerTitles: articles.map((a) => headerTitle(a)) };
  }

  window.typeset = typeset;
  window.hebNum = heb;
})();
