/* =====================================================================
   DEON — shared script
   Nav, reveal, formatting helpers, the service catalogue, a tiny local
   store (stand-in for the backend), and the home hero animation.
   ===================================================================== */

/* ── Business details: edit these ── */
const BUSINESS = {
  name: 'Deon',
  title: 'Software Developer',
  email: 'ceo@ardena.co.ke',
  phone: '0702 248 984',
  location: 'Kenya',
  pin: '', // KRA PIN, shown on invoices and receipts when set
};

/* ── Services: used by the home page, quote estimator, pay and invoice pages ── */
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

/* ── Services: rendered before the reveal observer so they animate in ── */
const ARROW = '<svg width="20" height="20" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const svgIcon = (name, size = 24) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;

// Home: large index rows
(() => {
  const list = $('#serviceRows');
  if (!list) return;
  list.innerHTML = SERVICES.map((s, i) => `
    <li data-anim style="--delay:${i * 60}ms">
      <a href="services.html#${s.id}">
        <span class="svc-row-icon">${svgIcon(s.icon)}</span>
        <span class="svc-row-name">${s.name}</span>
        <span class="svc-row-blurb">${s.blurb}</span>
        <span class="svc-row-arrow">${ARROW}</span>
      </a>
    </li>`).join('');
})();

// Services page: index + one chapter per service (ardenap layout)
(() => {
  const index = $('#svcIndex');
  const host = $('#svcChapters');
  if (!index || !host) return;
  const TONES = ['tone-white', 'tone-ink', 'tone-white', 'tone-green', 'tone-white', 'tone-ink'];
  index.innerHTML = SERVICES.map((s, i) =>
    `<li><a href="#${s.id}"><span class="muted">${String(i + 1).padStart(2, '0')}</span>${s.name}</a></li>`).join('');
  host.innerHTML = SERVICES.map((s, i) => {
    const dark = TONES[i] !== 'tone-white';
    return `
    <section class="chapter ${TONES[i]}" id="${s.id}" aria-labelledby="${s.id}-title">
      <div class="wrap">
        <div class="svc-top" data-anim>
          <span class="svc-icon">${svgIcon(s.icon, 28)}</span>
          <span class="svc-count muted">${String(i + 1).padStart(2, '0')} / ${String(SERVICES.length).padStart(2, '0')}</span>
        </div>
        <div class="grid12" style="margin-top:48px">
          <h2 id="${s.id}-title" class="type-statement mw-14 c-7" data-anim>${s.name}</h2>
          <p class="type-lede muted c-4 start-9 self-end" data-anim style="--delay:120ms">${s.lede}</p>
        </div>
        <div class="push" data-anim style="--delay:160ms">
          <ul class="included">${s.included.map((x, j) => `<li><span class="muted">${String(j + 1).padStart(2, '0')}</span>${x}</li>`).join('')}</ul>
          <div class="svc-foot">
            <p class="muted">Every project is priced to its scope. Tell me what you need and get a fixed quote within 24 hours.</p>
            <div class="svc-actions">
              <a href="quote.html?service=${s.id}" class="btn ${dark ? 'btn-white' : 'btn-ink'}">Request a quote</a>
              <a href="pay.html?service=${s.id}" class="text-link type-label">Pay for this</a>
            </div>
          </div>
        </div>
      </div>
    </section>`;
  }).join('');
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
   HERO — typed word ("I build ___")
   ===================================================================== */
(() => {
  const el = $('#typed');
  if (!el) return;
  const words = el.dataset.words.split(',');
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  let w = 0, i = words[0].length, deleting = true;
  const tick = () => {
    if (deleting) {
      i--;
      el.textContent = words[w].slice(0, i);
      if (i === 0) {
        deleting = false;
        w = (w + 1) % words.length;
        return setTimeout(tick, 260);
      }
      return setTimeout(tick, 45);
    }
    i++;
    el.textContent = words[w].slice(0, i);
    if (i === words[w].length) { deleting = true; return setTimeout(tick, 3000); }
    setTimeout(tick, 85);
  };
  setTimeout(tick, 3400);
})();

/* =====================================================================
   HERO — dot wave
   A plane of dots in perspective rolls like a slow swell beneath the
   headline, fading from deep emerald on the left to a lighter green on
   the right. The cursor (or a finger) lifts the ground beneath it, and
   now and then a ripple spreads out from a point on the plane.
   Density adapts to the screen, so it fits phones as well as desktops.
   Pauses off screen; one still frame under reduced motion.
   ===================================================================== */
(() => {
  const canvas = $('#heroField');
  const ctx = canvas?.getContext('2d');
  if (!canvas || !ctx) return;

  const DEEP  = [8, 81, 63];     // --green-deep
  const LIGHT = [46, 160, 120];  // lighter green
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

  const draw = (t) => {
    ctx.clearRect(0, 0, W, H);
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

  const tick = (t) => {
    ripples = ripples.filter((rp) => t - rp.start < 3200);
    if (t > nextRipple && ripples.length < 2) {
      ripples.push({ u: Math.random() * 1.4 - 0.7, v: 0.1 + Math.random() * 0.5, start: t });
      nextRipple = t + 2600 + Math.random() * 2600;
    }
    pointer.lift += ((pointer.x > -1e3 ? 1 : 0) - pointer.lift) * 0.06;
    draw(t);
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
    if (W === 0) stop();
    else if (reduced) draw(2000);
    else start();
  };

  new ResizeObserver(resize).observe(canvas);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; visible ? start() : stop(); }).observe(canvas);
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));

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
