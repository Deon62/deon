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
const ICONS = {
  globe:   '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  window:  '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 9h18M9 9v11"/>',
  phone:   '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2"/>',
  card:    '<rect x="2" y="5" width="20" height="14" rx="1"/><path d="M2 10h20M6 15h4"/>',
  wrench:  '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
  chat:    '<path d="M4 5h16v11H9l-5 4z"/>',
};
const SERVICES = [
  { id: 'website', name: 'Websites', from: 35000, unit: '', icon: 'globe',
    blurb: 'Fast, clean sites you can update yourself.',
    lede: 'A site that loads fast, looks right on every phone and tells people exactly what you do. Built so you can change the content yourself, with the domain, hosting and search setup handled.',
    included: ['Design that fits your brand', 'Pages you can edit yourself', 'Domain, hosting & email setup', 'Search and speed optimisation'] },
  { id: 'webapp', name: 'Web applications', from: 120000, unit: '', icon: 'window',
    blurb: 'Dashboards, portals and SaaS products.',
    lede: 'Internal tools, customer portals and full SaaS products, from the database to the last screen. Built to grow, documented so your team can own it.',
    included: ['Dashboards & admin panels', 'User accounts & roles', 'Database & API design', 'Reports & exports'] },
  { id: 'mobile', name: 'Mobile apps', from: 180000, unit: '', icon: 'phone',
    blurb: 'Android and iOS, released to both stores.',
    lede: 'One codebase, two stores. Apps that feel native on Android and iOS, with push notifications, offline support and the release process taken care of.',
    included: ['Android & iOS from one codebase', 'Push notifications', 'Offline-friendly', 'Play Store & App Store release'] },
  { id: 'payments', name: 'Payments & APIs', from: 40000, unit: '', icon: 'card',
    blurb: 'M-Pesa, cards and integrations.',
    lede: 'Get paid inside your own product. M-Pesa STK push, paybill and till, card payments, and connections to the tools you already use, with reconciliation built in.',
    included: ['M-Pesa STK push, paybill & till', 'Card payments', 'Payment reconciliation', 'Third-party API integrations'] },
  { id: 'care', name: 'Maintenance', from: 15000, unit: '/mo', icon: 'wrench',
    blurb: 'Hosting, updates and fixes, monthly.',
    lede: 'Your site or app kept online, secure and up to date every month. Bug fixes, backups and small improvements, without hunting for a developer each time.',
    included: ['Hosting & daily backups', 'Security updates', 'Bug fixes', 'Monthly hours for changes'] },
  { id: 'consult', name: 'Consultation', from: 3000, unit: '/hr', icon: 'chat',
    blurb: 'Scoping, reviews and technical advice.',
    lede: 'Before you spend on a build, talk it through. Scoping, cost estimates, architecture and code reviews, and straight answers on what to build and what to skip.',
    included: ['Project scoping & estimates', 'Architecture reviews', 'Code reviews', 'Build vs. buy advice'] },
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
    g.fillText(word, pad, pad + (m.fontBoundingBoxAscent ?? fs * 0.9));
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
