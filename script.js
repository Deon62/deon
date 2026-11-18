/* =====================================================================
   DEON — shared script
   Nav, reveal, formatting helpers, the service catalogue, a tiny local
   store (stand-in for the backend), and the home hero animation.
   ===================================================================== */

/* ── Business details: edit these ── */
const BUSINESS = {
  name: 'Deon Orina',
  title: 'Software Developer',
  email: 'ceo@ardena.co.ke',
  phone: '0702 248 984',
  location: 'Kenya',
  pin: '', // KRA PIN, shown on invoices and receipts when set
};

/* ── Services: names used by the quote and pay pages.
      The home and services pages have this content written into the HTML for SEO. ── */
const SERVICES = [
  { id: 'website', name: 'Websites' },
  { id: 'webapp', name: 'Web applications' },
  { id: 'mobile', name: 'Mobile apps' },
  { id: 'payments', name: 'Payments & APIs' },
  { id: 'ai', name: 'AI engineering' },
  { id: 'contracts', name: 'Smart contracts' },
  { id: 'data', name: 'Data science' },
  { id: 'care', name: 'Maintenance' },
  { id: 'consult', name: 'Consultation' },
];

/* ── Helpers ── */
const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const kes = (n) => 'KES ' + Math.round(Number(n) || 0).toLocaleString('en-KE');
const fmtDate = (d) => new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
const fmtDateTime = (d) => new Date(d).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const params = () => Object.fromEntries(new URLSearchParams(location.search));

/* Normalise a Kenyan number to 2547XXXXXXXX / 2541XXXXXXXX, or null. */
const normalisePhone = (raw) => {
  const d = String(raw || '').replace(/\D/g, '');
  const m = d.match(/^(?:254|0)?([17]\d{8})$/);
  return m ? '254' + m[1] : null;
};

/* Local store: a stand-in until the backend exists. */
const store = {
  get(key) { try { return JSON.parse(localStorage.getItem('deon.' + key)) || {}; } catch { return {}; } },
  put(key, id, value) { const all = store.get(key); all[id] = value; localStorage.setItem('deon.' + key, JSON.stringify(all)); return value; },
  find(key, id) { return store.get(key)[id] || null; },
};
const nextNumber = (prefix, key) => {
  const n = Object.keys(store.get(key)).length + 1;
  return `${prefix}-${new Date().getFullYear()}-${String(n).padStart(4, '0')}`;
};

/* Form submissions go to Formspree. Returns true on success. */
const FORMSPREE = 'https://formspree.io/f/xbgoyawp';
const sendForm = async (data) => {
  try {
    const res = await fetch(FORMSPREE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(data),
    });
    return res.ok;
  } catch {
    return false;
  }
};

const toast = (msg) => {
  let t = $('.toast');
  if (!t) { t = document.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status'); document.body.append(t); }
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove('show'), 2400);
};

/* ── Nav: scroll state + mobile drawer ── */
(() => {
  const nav = $('#nav');
  addEventListener('scroll', () => nav?.classList.toggle('scrolled', scrollY > 20), { passive: true });

  const toggle = $('#navToggle');
  const drawer = $('#navDrawer');
  if (!toggle || !drawer) return;
  const set = (open) => {
    drawer.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
    const s = toggle.querySelectorAll('span');
    s[0].style.transform = open ? 'rotate(45deg) translate(5px, 5px)' : '';
    s[1].style.opacity   = open ? '0' : '';
    s[2].style.transform = open ? 'rotate(-45deg) translate(5px, -5px)' : '';
  };
  toggle.addEventListener('click', () => set(!drawer.classList.contains('open')));
  $$('a', drawer).forEach((a) => a.addEventListener('click', () => set(false)));
  addEventListener('keydown', (e) => e.key === 'Escape' && set(false));
})();

/* =====================================================================
   MOTION — quiet details, all off under reduced motion
   ===================================================================== */
const MOTION_OK = !matchMedia('(prefers-reduced-motion: reduce)').matches;
const FINE_POINTER = matchMedia('(hover: hover) and (pointer: fine)').matches;

/* ── Headlines rise in line by line from behind a mask ── */
(() => {
  if (!MOTION_OK) return;
  const heads = $$('h1.type-statement, h2.type-statement').filter((h) => !h.children.length);
  const split = (h) => {
    const text = h.dataset.text || (h.dataset.text = h.textContent.trim().replace(/\s+/g, ' '));
    h.innerHTML = text.split(' ').map((w) => `<span class="w">${esc(w)}</span>`).join(' ');
    const lines = [];
    let top = null;
    $$('.w', h).forEach((w) => {
      if (w.offsetTop !== top) { lines.push([]); top = w.offsetTop; }
      lines[lines.length - 1].push(w.textContent);
    });
    h.innerHTML = lines.map((l, i) => `<span class="ln" style="--i:${i}"><span>${esc(l.join(' '))}</span></span>`).join('');
  };
  heads.forEach((h) => {
    if (!h.hasAttribute('aria-label')) h.setAttribute('aria-label', h.textContent.trim().replace(/\s+/g, ' '));
    h.classList.add('lines');
    split(h);
    // Page titles (no scroll trigger) reveal straight away.
    if (!h.hasAttribute('data-anim')) setTimeout(() => h.classList.add('in-view'), 80);
  });
  // Re-measure once the web font is in, and when the width changes.
  document.fonts?.ready.then(() => heads.forEach(split));
  let lastW = innerWidth;
  addEventListener('resize', () => {
    if (innerWidth === lastW) return;
    lastW = innerWidth;
    heads.forEach(split);
  });
})();

/* ── How it works: a line fills across the steps as you scroll ── */
(() => {
  const steps = $('.steps');
  if (!steps) return;
  const items = $$('li', steps);
  steps.classList.add('track');
  if (!MOTION_OK) return items.forEach((li) => { li.style.setProperty('--fill', 1); li.classList.add('lit'); });
  let raf = 0;
  const update = () => {
    raf = 0;
    const r = steps.getBoundingClientRect();
    const start = innerHeight * 0.85, end = innerHeight * 0.35;
    const p = Math.min(1, Math.max(0, (start - r.top) / (start - end + r.height * 0.4)));
    items.forEach((li, i) => {
      const f = Math.min(1, Math.max(0, p * items.length - i));
      li.style.setProperty('--fill', f.toFixed(3));
      li.classList.toggle('lit', f >= 1);
    });
  };
  addEventListener('scroll', () => { if (!raf) raf = requestAnimationFrame(update); }, { passive: true });
  addEventListener('resize', update);
  update();
})();

/* ── Selected work: a live preview follows the cursor over each project ── */
(() => {
  const rows = $$('[data-preview]');
  if (!rows.length || !FINE_POINTER || !MOTION_OK) return;
  const box = document.createElement('div');
  box.className = 'work-preview';
  box.setAttribute('aria-hidden', 'true');
  box.innerHTML = '<img alt="" />';
  document.body.append(box);
  const img = box.firstChild;
  rows.forEach((r) => { const i = new Image(); i.src = r.dataset.preview; }); // preload

  let x = 0, y = 0, tx = 0, ty = 0, raf = 0, active = false;
  const loop = () => {
    const dx = tx - x;
    x += dx * 0.16; y += (ty - y) * 0.16;
    const tilt = Math.max(-10, Math.min(10, dx * 0.12));
    box.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%) rotate(${tilt}deg)`;
    raf = active || Math.abs(dx) > 0.5 ? requestAnimationFrame(loop) : 0;
  };
  const move = (e) => { tx = Math.min(e.clientX + 120, innerWidth - 190); ty = e.clientY; if (!raf) raf = requestAnimationFrame(loop); };
  rows.forEach((r) => {
    r.addEventListener('pointerenter', (e) => {
      if (!active) { x = tx = e.clientX + 120; y = ty = e.clientY; }
      active = true;
      img.src = r.dataset.preview;
      box.classList.add('show');
      move(e);
    });
    r.addEventListener('pointermove', move);
    r.addEventListener('pointerleave', () => { active = false; box.classList.remove('show'); });
  });
  addEventListener('scroll', () => { if (active) { active = false; box.classList.remove('show'); } }, { passive: true });
})();

/* ── About: the portrait assembles from green halftone dots, then resolves ── */
(() => {
  const fig = $('.about-photo');
  const photo = fig?.querySelector('img');
  if (!fig || !photo || !MOTION_OK) return;
  fig.classList.add('dots');
  const canvas = document.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  fig.append(canvas);
  const ctx = canvas.getContext('2d');

  const run = () => {
    const W = fig.clientWidth, H = fig.clientHeight, dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // Sample the photo at the figure's size (object-fit: cover, top).
    const off = document.createElement('canvas');
    off.width = W; off.height = H;
    const g = off.getContext('2d', { willReadFrequently: true });
    const r = Math.max(W / photo.naturalWidth, H / photo.naturalHeight);
    g.drawImage(photo, (W - photo.naturalWidth * r) / 2, 0, photo.naturalWidth * r, photo.naturalHeight * r);
    const data = g.getImageData(0, 0, W, H).data;
    const step = Math.max(6, Math.round(W / 64));
    const dots = [];
    for (let py = step / 2; py < H; py += step) {
      for (let px = step / 2; px < W; px += step) {
        const i = ((py | 0) * W + (px | 0)) * 4;
        const lum = (data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114) / 255;
        const dark = Math.pow(1 - lum, 1.6); // ease the midtones so features read
        if (dark < 0.06) continue;
        dots.push({
          x: px, y: py, r: Math.min(step * 0.6, step * 0.62 * dark + 0.45),
          sx: px + (Math.random() - 0.5) * W * 0.6, sy: H + Math.random() * H * 0.5,
          d: (1 - py / H) * 500 + Math.random() * 300,
          c: dark > 0.55 ? '#16181D' : dark > 0.25 ? '#08513F' : '#2EA078',
        });
      }
    }
    const t0 = performance.now(), FLY = 1100;
    const ease = (t) => 1 - Math.pow(1 - t, 3);
    const frame = (now) => {
      const t = now - t0;
      ctx.clearRect(0, 0, W, H);
      let done = true;
      for (const p of dots) {
        const e = Math.min(1, Math.max(0, (t - p.d) / FLY));
        if (e < 1) done = false;
        if (e === 0) continue;
        const k = ease(e);
        ctx.globalAlpha = k;
        ctx.fillStyle = p.c;
        ctx.beginPath();
        ctx.arc(p.sx + (p.x - p.sx) * k, p.sy + (p.y - p.sy) * k, p.r, 0, 6.283);
        ctx.fill();
      }
      if (!done) return requestAnimationFrame(frame);
      // Hold the halftone for a beat, then let the photo resolve through it.
      setTimeout(() => fig.classList.add('resolved'), 450);
    };
    requestAnimationFrame(frame);
  };

  const ready = () => new IntersectionObserver(([e], io) => {
    if (e.isIntersecting) { io.disconnect(); setTimeout(run, 250); }
  }, { threshold: 0.3 }).observe(fig);
  photo.complete && photo.naturalWidth ? ready() : photo.addEventListener('load', ready, { once: true });
})();

/* ── Reveal on scroll ── */
(() => {
  const els = $$('[data-anim]');
  if (!('IntersectionObserver' in window)) return els.forEach((el) => el.classList.add('in-view'));
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add('in-view'); io.unobserve(e.target); }
  }), { threshold: 0.1, rootMargin: '0px 0px -48px 0px' });
  els.forEach((el) => io.observe(el));
})();

/* ── Footer year ── */
$$('[data-year]').forEach((el) => (el.textContent = new Date().getFullYear()));

/* =====================================================================
   HERO — dot wave + words made of the wave
   A plane of dots in perspective rolls like a slow swell beneath the
   headline. The headline's changing word is not typed: dots lift off
   the wave, fly up along curved paths and assemble into the word,
   letter by letter from left to right. While it holds, the word
   shimmers and scatters away from the cursor, then the dots fall back
   into the wave just as the next word rises out of it.
   The real word stays in the HTML (transparent while the effect runs)
   for search engines, screen readers and copy/paste.
   Pauses off screen; still frame and plain text under reduced motion.
   ===================================================================== */
(() => {
  const canvas = $('#heroField');
  const ctx = canvas?.getContext('2d');
  if (!canvas || !ctx) return;

  const DEEP  = [8, 81, 63];          // --green-deep
  const LIGHT = [46, 160, 120];       // lighter green
  const CREST = 'rgb(159, 224, 193)'; // --mint
  const SHADES = 24;
  const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const palette = Array.from({ length: SHADES }, (_, i) => `rgb(${mix(DEEP, LIGHT, i / (SHADES - 1)).join(',')})`);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  let W = 0, H = 0, frame = 0, running = false, visible = true;
  let cols = 0, rows = 0, ripples = [], nextRipple = 1500;
  const pointer = { x: -1e4, y: -1e4, lift: 0 };

  const grid = () => {
    cols = Math.round(Math.min(Math.max(W / 13, 44), 130));
    rows = Math.round(Math.min(Math.max(H / 20, 26), 48));
  };

  // u across (-1..1), v into the distance (0 near .. 1 far)
  const project = (u, v, h) => {
    const depth = 1 + v * 3.2;
    const horizon = H * 0.66;
    const ground = H * 0.38;
    return { x: W / 2 + (u * W * 0.95) / depth, y: horizon + (ground - h * H * 0.07) / depth };
  };

  const drawWave = (t) => {
    for (let r = rows - 1; r >= 0; r--) {
      const v = r / (rows - 1);
      for (let c = 0; c < cols; c++) {
        const u = (c / (cols - 1)) * 2 - 1;
        let h =
          Math.sin(u * 3.2 + t * 0.00055) * 0.55 +
          Math.sin(v * 7.0 - t * 0.0007) * 0.45 +
          Math.sin((u + v) * 5.0 + t * 0.0004) * 0.3;

        for (const rp of ripples) {
          const age = (t - rp.start) / 1000;
          const band = Math.hypot(u - rp.u, (v - rp.v) * 1.6) - age * 0.55;
          if (Math.abs(band) < 0.25) h += Math.cos(band * 18) * (1 - Math.abs(band) / 0.25) * 1.4 * Math.max(0, 1 - age / 3.2);
        }

        let p = project(u, v, h);
        const dx = p.x - pointer.x, dy = p.y - pointer.y, d2 = dx * dx + dy * dy;
        if (d2 < 40000) { h += Math.exp(-d2 / 9000) * 3.2 * pointer.lift; p = project(u, v, h); }

        const near = 1 - v;
        const size = 0.8 + near * 2.1 + Math.max(0, h) * 0.2;
        const edge = 1 - Math.abs(u) * 0.55;
        ctx.globalAlpha = Math.min((0.1 + near * 0.8 + Math.max(0, h) * 0.08) * edge, 0.9);
        ctx.fillStyle = h > 1.15 ? CREST : palette[Math.round(((u + 1) / 2) * (SHADES - 1))];
        ctx.fillRect(p.x - size / 2, p.y - size / 2, size, size);
      }
    }
    ctx.globalAlpha = 1;
  };

  /* ── Words made of the wave ── */
  const slot = $('#heroWord');
  const WORDS = slot ? slot.dataset.words.split(',') : [];
  const HOLD = 2800;
  let groups = [], wordIndex = 0, nextSwitch = Infinity, live = false, lastWidth = 0;
  const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const easeIn = (t) => t * t * t;
  const fromWave = () => project(Math.random() * 1.6 - 0.8, 0.08 + Math.random() * 0.42, 0);

  // Lay the word out in the real headline, then sample its pixels.
  const sampleWord = (word) => {
    slot.textContent = word;
    const r = slot.getBoundingClientRect(), c = canvas.getBoundingClientRect();
    const cs = getComputedStyle(slot);
    const fs = parseFloat(cs.fontSize);
    const step = Math.max(2.6, fs / 17);
    const pad = Math.ceil(fs * 0.25);
    const w = Math.ceil(r.width + pad * 2), h = Math.ceil(r.height + pad * 2);
    const off = document.createElement('canvas');
    off.width = w; off.height = h;
    const g = off.getContext('2d', { willReadFrequently: true });
    g.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    if ('letterSpacing' in g) g.letterSpacing = cs.letterSpacing;
    const m = g.measureText(word);
    // The slot is inline-block, so its box is the line height; centre the glyphs' content area in it.
    const A = m.fontBoundingBoxAscent ?? fs * 0.9, D = m.fontBoundingBoxDescent ?? fs * 0.25;
    g.fillText(word, pad, pad + (r.height - (A + D)) / 2 + A);
    const data = g.getImageData(0, 0, w, h).data;
    const ox = r.left - c.left - pad, oy = r.top - c.top - pad;
    const pts = [];
    for (let y = 0; y < h; y += step)
      for (let x = 0; x < w; x += step)
        if (data[((y | 0) * w + (x | 0)) * 4 + 3] > 140) pts.push([ox + x, oy + y]);
    return { pts, size: step * 0.82, left: r.left - c.left, width: r.width || 1 };
  };

  const retire = (t) => groups.forEach((gr) => {
    if (gr.falling) return;
    gr.falling = true;
    gr.parts.forEach((p) => {
      const d = fromWave();
      Object.assign(p, { fx: p.x, fy: p.y, dx: d.x, dy: d.y, t0: t + Math.random() * 380, dur: 650 + Math.random() * 500 });
    });
  });

  const spawn = (t, instant = false) => {
    retire(t);
    const { pts, size, left, width } = sampleWord(WORDS[wordIndex]);
    const parts = pts.map(([x, y]) => {
      const s = fromWave();
      const k = Math.min(1, Math.max(0, (x - left) / width));
      return {
        sx: s.x, sy: s.y, tx: x, ty: y, x: s.x, y: s.y, ox: 0, oy: 0, vx: 0, vy: 0, size,
        t0: instant ? t - 5000 : t + 120 + k * 520 + Math.random() * 380,
        dur: 900 + Math.random() * 600,
        curve: (Math.random() - 0.5) * 180,
        phase: Math.random() * 6.283,
        color: Math.random() < 0.1 ? CREST : palette[Math.min(SHADES - 1, Math.round(k * (SHADES - 1)))],
      };
    });
    groups.push({ parts, falling: false });
    nextSwitch = t + 1800 + HOLD;
    wordIndex = (wordIndex + 1) % WORDS.length;
  };

  const drawWords = (t) => {
    if (!live) return;
    if (t > nextSwitch) spawn(t);
    groups = groups.filter((gr) => !gr.falling || gr.parts.some((p) => t < p.t0 + p.dur));
    for (const gr of groups) {
      for (const p of gr.parts) {
        let x, y, a;
        if (gr.falling) {
          const e = Math.min(1, Math.max(0, (t - p.t0) / p.dur));
          if (e >= 1) continue;
          const k = easeIn(e);
          x = p.fx + (p.dx - p.fx) * k;
          y = p.fy + (p.dy - p.fy) * k;
          a = 1 - e * 0.8;
        } else {
          const e = Math.min(1, Math.max(0, (t - p.t0) / p.dur));
          if (e === 0) continue; // still part of the wave
          const k = easeInOut(e);
          x = p.sx + (p.tx - p.sx) * k + Math.sin(Math.PI * k) * p.curve;
          y = p.sy + (p.ty - p.sy) * k;
          if (e >= 1) {
            // Holding: spring back from the cursor, with a faint shimmer.
            const ddx = x + p.ox - pointer.x, ddy = y + p.oy - pointer.y, d2 = ddx * ddx + ddy * ddy;
            if (d2 < 6400 && pointer.lift > 0.5) {
              const d = Math.sqrt(d2) || 1, f = (1 - d / 80) * 2.4;
              p.vx += (ddx / d) * f; p.vy += (ddy / d) * f;
            }
            p.vx = (p.vx - p.ox * 0.07) * 0.82;
            p.vy = (p.vy - p.oy * 0.07) * 0.82;
            p.ox += p.vx; p.oy += p.vy;
            x += p.ox + Math.sin(t * 0.002 + p.phase) * 0.35;
            y += p.oy + Math.cos(t * 0.0023 + p.phase) * 0.35;
          }
          a = 0.3 + 0.7 * k;
          p.x = x; p.y = y;
        }
        ctx.globalAlpha = a;
        ctx.fillStyle = p.color;
        ctx.fillRect(x - p.size / 2, y - p.size / 2, p.size, p.size);
      }
    }
    ctx.globalAlpha = 1;
  };

  const tick = (t) => {
    ripples = ripples.filter((rp) => t - rp.start < 3200);
    if (t > nextRipple && ripples.length < 2) {
      ripples.push({ u: Math.random() * 1.4 - 0.7, v: 0.1 + Math.random() * 0.5, start: t });
      nextRipple = t + 2600 + Math.random() * 2600;
    }
    pointer.lift += ((pointer.x > -1e3 ? 1 : 0) - pointer.lift) * 0.06;
    ctx.clearRect(0, 0, W, H);
    drawWave(t);
    drawWords(t);
    frame = requestAnimationFrame(tick);
  };

  const start = () => {
    if (running || reduced || !visible || document.hidden || W === 0) return;
    running = true;
    frame = requestAnimationFrame(tick);
  };
  const stop = () => { running = false; cancelAnimationFrame(frame); };

  const resize = () => {
    const r = canvas.getBoundingClientRect();
    const dpr = Math.min(devicePixelRatio || 1, 2);
    W = r.width; H = r.height;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    grid();
    // Re-lay the current word if the width changed (not on mobile toolbar height changes).
    if (live && W !== lastWidth) {
      groups = [];
      wordIndex = (wordIndex - 1 + WORDS.length) % WORDS.length;
      spawn(performance.now(), true);
    }
    lastWidth = W;
    if (W === 0) stop();
    else if (reduced) { ctx.clearRect(0, 0, W, H); drawWave(2000); }
    else start();
  };

  new ResizeObserver(resize).observe(canvas);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; visible ? start() : stop(); }).observe(canvas);
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));

  // Start the word effect once the headline font is ready, so the shapes match.
  if (slot && WORDS.length && !reduced) {
    // Wait for the font, and for the headline's own fade-in to finish.
    (document.fonts?.ready || Promise.resolve()).then(() => new Promise((r) => setTimeout(r, 1000))).then(() => {
      live = true;
      slot.classList.add('is-live');
      lastWidth = W;
      spawn(performance.now());
    });
  }

  // The canvas sits behind the copy, so listen on the page. Touch works too.
  addEventListener('pointermove', (e) => {
    const r = canvas.getBoundingClientRect();
    pointer.x = e.clientX - r.left;
    pointer.y = e.clientY - r.top;
  }, { passive: true });
  const clear = () => { pointer.x = pointer.y = -1e4; };
  document.documentElement.addEventListener('pointerleave', clear);
  addEventListener('pointerup', (e) => e.pointerType === 'touch' && clear());
})();
