/* Timeline component (standalone, dependency-free): the navigation hub of skill-history.
 *
 * Spec source: spec #21 / ADR-0001:
 *   - Ticks positioned proportionally by commit date (not evenly by version index); one tick per commit, tagged commits carry a tag label
 *   - Dual handles (baseline A / compare B) drag with auto-anchoring to the nearest commit; hover highlight + tooltip; click a tick to jump
 *   - Quick ranges 7/14/30/180 days; wheel zoom, drag empty space to pan
 *   - Cumulative +N −M and the time span shown centered on the interval
 *
 * Usage: SkillTimeline.mount(container, {versions, ia, ib, onChange, labels})
 * Theming rides the page's CSS variables (--blue/--purple/--orange/…); the component injects its own styles and works standalone.
 */
"use strict";
(function () {
  const CSS = `
.tl{--tl-h:44px;user-select:none}
.tl-stage{position:relative;height:var(--tl-h);cursor:grab;touch-action:none}
.tl-stage.panning{cursor:grabbing}
.tl-stage.dragging{cursor:grabbing}
.tl-line{position:absolute;top:28px;left:0;right:0;height:2px;background:var(--line);border-radius:1px}
.tl-band{position:absolute;top:25px;height:8px;background:color-mix(in srgb,var(--blue) 18%,transparent);
         border-radius:4px;pointer-events:none}
.tl-tick{position:absolute;top:25px;width:8px;height:8px;margin:-4px 0 0 -4px;border-radius:5px;
         background:var(--panel2);border:1px solid var(--gutter);pointer-events:none;transition:transform .1s}
.tl-tick.hot{transform:scale(1.7);background:var(--dim);z-index:3}
.tl-tick.tagged{border-color:var(--orange);background:color-mix(in srgb,var(--orange) 45%,var(--panel2))}
.tl-tick.anchor-a{background:var(--blue);border-color:var(--blue)}
.tl-tick.anchor-b{background:var(--purple);border-color:var(--purple)}
.tl-tag{position:absolute;top:2px;transform:translateX(-50%);white-space:nowrap;
        font-family:var(--font-mono);font-size:9.5px;color:var(--orange);
        background:color-mix(in srgb,var(--orange) 14%,transparent);
        border:1px solid color-mix(in srgb,var(--orange) 40%,transparent);
        padding:0 6px;border-radius:5px;pointer-events:none;height:16px;line-height:15px}
.tl-tag.hidden{visibility:hidden}
.tl-handle{position:absolute;top:18px;width:28px;height:28px;margin-left:-14px;border-radius:15px;
           background:transparent;border:0;padding:0;cursor:grab;z-index:5}
.tl-handle:active{cursor:grabbing}
.tl-handle:focus-visible{outline:2px solid var(--dim);outline-offset:2px}
.tl-handle .halo{position:absolute;inset:3px;border-radius:15px;border:1.5px solid var(--blue);
                 background:var(--bg);opacity:.85}
.tl-handle .thumb{position:absolute;left:9px;top:9px;width:10px;height:10px;border-radius:6px;background:var(--blue)}
.tl-handle.hb .halo{border-color:var(--purple)}
.tl-handle.hb .thumb{background:var(--purple)}
.tl-tip{position:absolute;bottom:calc(100% + 6px);transform:translateX(-50%);white-space:nowrap;
        pointer-events:none;opacity:0;transition:opacity .1s;z-index:8;
        font-family:var(--font-mono);font-size:9.5px;line-height:1.5;text-align:left;
        background:var(--panel);border:1px solid var(--line);border-radius:7px;
        padding:4px 9px;color:var(--text);box-shadow:0 6px 18px #00000070}
.tl-tip.show{opacity:1}
.tl-tip .tg{color:var(--orange)}
.tl-tip .up{color:var(--green)}.tl-tip .dn{color:var(--red)}.tl-tip .dim{color:var(--faint)}
.tl-quick{display:flex;gap:4px;align-items:center;flex:none}
.tl-quick .qlbl{font-size:9.5px;color:var(--faint);letter-spacing:.5px;margin-right:2px}
.tl-quick button{border:1px solid var(--line);background:none;color:var(--faint);
                 font-family:var(--font-mono);font-size:9.5px;padding:1px 7px;border-radius:6px;cursor:pointer}
.tl-quick button:hover{color:var(--text);border-color:var(--dim)}
.tl-quick button.on{color:var(--blue);border-color:var(--blue);
                    background:color-mix(in srgb,var(--blue) 12%,transparent)}
.tl-row{display:flex;align-items:flex-start;gap:12px}
.tl-row .tl-quick{padding-top:8px}
.tl-dates{flex:1;display:flex;align-items:center;gap:10px;font-family:var(--font-mono);font-size:10.5px}
.tl-dates .da{color:var(--blue);white-space:nowrap}
.tl-dates .db{color:var(--purple);white-space:nowrap}
.tl-dates .dsp{flex:1;height:1px;background:var(--dimline);min-width:8px}
.tl-dates .mid{display:flex;gap:6px;align-items:center;white-space:nowrap;
               background:color-mix(in srgb,var(--orange) 16%,transparent);
               border-radius:6px;padding:1px 8px}
.tl-dates .mid .up{color:var(--green)}.tl-dates .mid .dn{color:var(--red)}
.tl-dates .mid .span{color:var(--dim);font-size:9.5px}
`;

  const DEFAULT_LABELS = {
    quick: "Quick", all: "All", days: "d", singleTp: "Single timepoint",
    latest: "Latest", noPrev: "—",
    handleA: "Baseline timepoint", handleB: "Compare timepoint"
  };
  const DAY = 86400000;
  const pad2 = n => String(n).padStart(2, "0");
  const iso = t => { const d = new Date(t); return d.getUTCFullYear() + "-" + pad2(d.getUTCMonth() + 1) + "-" + pad2(d.getUTCDate()); };
  const parseD = s => Date.parse(s + "T00:00:00Z");

  function injectCss() {
    if (document.getElementById("tl-css")) return;
    const st = document.createElement("style");
    st.id = "tl-css";
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function cumulative(vs, ia, ib) {
    let added = 0, removed = 0;
    for (let i = ia + 1; i <= ib; i++) {
      const c = vs[i].change;
      if (c) { added += c.added; removed += c.removed; }
    }
    return { added, removed };
  }

  function mount(el, opts) {
    injectCss();
    const vs = opts.versions || [];
    const labels = Object.assign({}, DEFAULT_LABELS, opts.labels || {});
    const n = vs.length;
    const ts = vs.map(v => parseD(v.date));
    const disabled = n < 2;
    let ia = Math.max(0, Math.min((opts.ia == null ? n - 2 : opts.ia), n - 1));
    let ib = Math.max(0, Math.min((opts.ib == null ? n - 1 : opts.ib), n - 1));
    if (disabled) { ia = 0; ib = Math.max(0, n - 1); }

    const minT = ts.length ? Math.min(...ts) : 0;
    const maxT = ts.length ? Math.max(...ts) : DAY;
    const dataSpan = Math.max(maxT - minT, DAY);          // all same-day → degrade to a 1-day span
    const domLo = minT - dataSpan * 0.04, domHi = maxT + dataSpan * 0.04;
    let w0 = domLo, w1 = domHi;

    el.classList.add("tl");
    el.innerHTML = `
      <div class="tl-row">
        <div class="tl-quick">
          <span class="qlbl">${esc(labels.quick)}</span>
          ${[7, 14, 30, 180].map(d => `<button data-range="${d}">${d}${esc(labels.days)}</button>`).join("")}
          <button data-range="all">${esc(labels.all)}</button>
        </div>
        <div class="tl-dates">
          <span class="da"></span><span class="dsp"></span>
          <span class="mid"></span>
          <span class="dsp"></span><span class="db"></span>
        </div>
      </div>
      <div class="tl-stage" data-win-start="" data-win-end="">
        <div class="tl-line"></div><div class="tl-band"></div>
        <button class="tl-handle ha" data-h="a" tabindex="0" aria-label="${esc(labels.handleA)}">
          <span class="halo"></span><span class="thumb"></span></button>
        <button class="tl-handle hb" data-h="b" tabindex="0" aria-label="${esc(labels.handleB)}">
          <span class="halo"></span><span class="thumb"></span></button>
        <div class="tl-tip"></div>
      </div>`;
    const stage = el.querySelector(".tl-stage");
    const band = el.querySelector(".tl-band");
    const tip = el.querySelector(".tl-tip");
    const ha = el.querySelector(".tl-handle.ha");
    const hb = el.querySelector(".tl-handle.hb");
    const daEl = el.querySelector(".tl-dates .da");
    const dbEl = el.querySelector(".tl-dates .db");
    const midEl = el.querySelector(".tl-dates .mid");
    const quickBtns = el.querySelectorAll("[data-range]");

    const W = () => stage.clientWidth || 1;
    const PADX = 12;
    const xOf = t => PADX + (t - w0) / (w1 - w0) * (W() - 2 * PADX);
    const tOf = x => w0 + (x - PADX) / (W() - 2 * PADX) * (w1 - w0);
    const clampWin = () => {
      if (w1 - w0 < 2 * DAY) { const c = (w0 + w1) / 2; w0 = c - DAY; w1 = c + DAY; }
      if (w0 < domLo) { w1 += domLo - w0; w0 = domLo; }
      if (w1 > domHi) { w0 -= w1 - domHi; w1 = domHi; }
      if (w0 < domLo) w0 = domLo;
    };
    // Anchor: nearest commit (on ties, prefer the one closer to the current handle to avoid jumping on burst days)
    function snap(t, from) {
      let best = 0, bd = Infinity, bi = Math.abs(from || 0);
      for (let i = 0; i < n; i++) {
        const d = Math.abs(ts[i] - t);
        const tie = d === bd && Math.abs(i - (from || 0)) < bi;
        if (d < bd || tie) { bd = d; best = i; bi = Math.abs(i - (from || 0)); }
      }
      return best;
    }
    function setSel(a, b, commit) {
      if (a === ia && b === ib && !commit) return;
      ia = a; ib = b;
      drawSel();                                   // self-draw while dragging; commit back to the host on release
      if (commit && opts.onChange) opts.onChange(ia, ib);
    }
    function vLabel(i) {
      const v = vs[i];
      return v.date + " · " + String(v.sha).slice(0, 7) + (i === n - 1 ? " · " + labels.latest : "");
    }

    function drawTicks() {
      stage.querySelectorAll(".tl-tick,.tl-tag").forEach(e => e.remove());
      const shown = [];
      for (let i = 0; i < n; i++) {
        const x = xOf(ts[i]);
        if (x < -4 || x > W() + 4) continue;    // outside the window; redrawn after pan/zoom
        const tick = document.createElement("div");
        tick.className = "tl-tick" + (vs[i].tags && vs[i].tags.length ? " tagged" : "");
        tick.style.left = x + "px";
        tick.setAttribute("data-dot", i);
        tick.setAttribute("data-t", ts[i]);
        stage.appendChild(tick);
        if (vs[i].tags && vs[i].tags.length) {
          const tag = document.createElement("span");
          const name = vs[i].tags.find(x => /^skill-|^v/.test(x)) || vs[i].tags[0];
          const extra = vs[i].tags.length > 1 ? "+" + (vs[i].tags.length - 1) : "";
          tag.className = "tl-tag";
          tag.textContent = name + extra;
          tag.style.left = x + "px";
          stage.appendChild(tag);
          const estW = tag.textContent.length * 6.2 + 14;
          const last = shown[shown.length - 1];
          if (last && x - last.x < (last.w + estW) / 2 + 4) tag.classList.add("hidden");
          else shown.push({ x, w: estW });
        }
      }
      stage.setAttribute("data-win-start", iso(w0));
      stage.setAttribute("data-win-end", iso(w1));
    }
    function drawSel() {
      const xa = xOf(ts[ia]), xb = xOf(ts[ib]);
      ha.style.left = xa + "px";
      hb.style.left = xb + "px";
      band.style.left = xa + "px";
      band.style.width = Math.max(0, xb - xa) + "px";
      stage.querySelectorAll(".tl-tick").forEach(tk => {
        const i = +tk.getAttribute("data-dot");
        tk.classList.toggle("anchor-a", i === ia);
        tk.classList.toggle("anchor-b", i === ib);
      });
      daEl.textContent = vLabel(ia);
      dbEl.textContent = vLabel(ib);
      const c = cumulative(vs, ia, ib);
      const days = Math.max(0, Math.round((ts[ib] - ts[ia]) / DAY));
      midEl.innerHTML = `<b class="up">+${c.added}</b><b class="dn">−${c.removed}</b>` +
        `<span class="span">· ${days} ${esc(labels.days)}</span>`;
      ha.setAttribute("aria-valuetext", vLabel(ia));
      hb.setAttribute("aria-valuetext", vLabel(ib));
      quickBtns.forEach(b => b.classList.remove("on"));
    }
    function drawAll() { drawTicks(); drawSel(); markQuick(); }

    function markQuick() {
      const span = w1 - w0;
      quickBtns.forEach(b => {
        const r = b.getAttribute("data-range");
        if (r === "all") b.classList.toggle("on", span >= (domHi - domLo) * 0.98);
        else b.classList.toggle("on", Math.abs(span - (+r) * DAY) < DAY * 0.6);
      });
    }
    function quick(r) {
      if (r === "all") { w0 = domLo; w1 = domHi; }
      else {
        const anchor = ts[ib];
        w1 = Math.min(domHi, anchor + (+r) * DAY * 0.12);
        w0 = Math.max(domLo, w1 - (+r) * DAY);
        if (w1 - w0 < (+r) * DAY) w1 = Math.min(domHi, w0 + (+r) * DAY);
      }
      clampWin(); drawAll();
    }

    /* ── Pointer interaction: handle drag / empty-space pan / wheel zoom ── */
    let mode = null;             // "a" | "b" | "pan"
    let panX = 0, panW0 = 0, panW1 = 0, panned = false;
    function dragA(x) {
      const t = tOf(Math.max(PADX, Math.min(W() - PADX, x)));
      let i = snap(t, ia);
      if (i >= ib) i = ib - 1;
      if (i !== ia) setSel(i, ib, false);
    }
    function dragB(x) {
      const t = tOf(Math.max(PADX, Math.min(W() - PADX, x)));
      let i = snap(t, ib);
      if (i <= ia) i = ia + 1;
      if (i !== ib) setSel(ia, i, false);
    }
    stage.addEventListener("pointerdown", e => {
      const h = e.target.closest("[data-h]");
      if (h) { mode = h.getAttribute("data-h"); stage.classList.add("dragging"); }
      else {
        mode = "pan"; panX = e.clientX; panW0 = w0; panW1 = w1; panned = false;
        stage.classList.add("panning");
      }
      stage.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    stage.addEventListener("pointermove", e => {
      if (mode === "a") dragA(px(e));
      else if (mode === "b") dragB(px(e));
      else if (mode === "pan") {
        const dx = e.clientX - panX;
        if (Math.abs(dx) > 3) panned = true;
        const dt = -dx / (W() - 2 * PADX) * (panW1 - panW0);
        w0 = panW0 + dt; w1 = panW1 + dt; clampWin(); drawAll();
      }
    });
    const endDrag = e => {
      if (mode === "a" || mode === "b") { if (opts.onChange) opts.onChange(ia, ib); }
      mode = null;
      stage.classList.remove("dragging", "panning");
    };
    stage.addEventListener("pointerup", endDrag);
    stage.addEventListener("pointercancel", endDrag);
    function px(e) {
      const r = stage.getBoundingClientRect();
      return e.clientX - r.left;
    }

    /* Wheel zoom (centered on the cursor) */
    stage.addEventListener("wheel", e => {
      if (disabled) return;
      e.preventDefault();
      const f = Math.exp(e.deltaY * 0.0016);
      const c = tOf(px(e));
      w0 = c - (c - w0) * f; w1 = c + (w1 - c) * f;
      clampWin(); drawAll();
    }, { passive: false });

    /* Hover/click by proximity: ticks of same-day burst commits overlap fully, element-level hover would occlude */
    function nearestTick(x) {
      let best = -1, bd = 9;
      for (let i = 0; i < n; i++) {
        const d = Math.abs(xOf(ts[i]) - x);
        if (d < bd) { bd = d; best = i; }
      }
      return best;
    }
    let hot = -1;
    stage.addEventListener("pointermove", e => {
      if (mode) return;
      const i = nearestTick(px(e));
      if (i !== hot) {
        stage.querySelectorAll(".tl-tick.hot").forEach(t => t.classList.remove("hot"));
        hot = i;
        const tk = stage.querySelector(`.tl-tick[data-dot="${i}"]`);
        if (tk) tk.classList.add("hot");
      }
      if (i < 0) { tip.classList.remove("show"); return; }
      const v = vs[i];
      const tagLine = v.tags && v.tags.length ? `<div class="tg">${esc(v.tags.join(", "))}</div>` : "";
      const chg = v.change
        ? `<span class="up">+${v.change.added}</span> <span class="dn">−${v.change.removed}</span>`
        : `<span class="dim">${esc(labels.noPrev)}</span>`;
      tip.innerHTML = `<div>${esc(v.date)} · ${esc(String(v.sha).slice(0, 7))}</div>${tagLine}` +
        `<div>${chg} <span class="dim">· ${v.lines == null ? "" : v.lines}</span></div>`;
      tip.style.left = xOf(ts[i]) + "px";
      tip.classList.add("show");
    });
    stage.addEventListener("pointerleave", () => {
      tip.classList.remove("show");
      stage.querySelectorAll(".tl-tick.hot").forEach(t => t.classList.remove("hot"));
      hot = -1;
    });

    /* Click a tick: moves the nearer of the two handles (clicks right after a pan don't count) */
    stage.addEventListener("click", e => {
      if (disabled || panned) return;
      const i = nearestTick(px(e));
      if (i < 0 || i === ia || i === ib) return;
      const xa = xOf(ts[ia]), xb = xOf(ts[ib]), xc = xOf(ts[i]);
      if (Math.abs(xc - xa) <= Math.abs(xc - xb) && i < ib) setSel(i, ib, true);
      else if (i > ia) setSel(ia, i, true);
    });

    /* Keyboard: arrow keys step between commits */
    [ha, hb].forEach(h => h.addEventListener("keydown", e => {
      if (disabled) return;
      const isA = h.getAttribute("data-h") === "a";
      const d = e.key === "ArrowLeft" ? -1 : e.key === "ArrowRight" ? 1 : 0;
      if (!d) return;
      e.preventDefault();
      if (isA) setSel(Math.max(0, Math.min(ia + d, ib - 1)), ib, true);
      else setSel(ia, Math.min(n - 1, Math.max(ib + d, ia + 1)), true);
    }));

    quickBtns.forEach(b => b.addEventListener("click", () => quick(b.getAttribute("data-range"))));

    let rW = 0;
    new ResizeObserver(() => {
      clearTimeout(rW);
      rW = setTimeout(drawAll, 50);
    }).observe(stage);

    if (disabled) {
      el.querySelectorAll(".tl-handle,.tl-quick button").forEach(x => (x.disabled = true));
      midEl.innerHTML = `<span class="span">${esc(labels.singleTp)}</span>`;
    }
    drawAll();
  }

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  }

  window.SkillTimeline = { mount };
})();
