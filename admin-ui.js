/* =====================================================================
   DEON — admin shell, shared by /admin and /invoice
   Sidebar, sign-in gate, access checks, confirm dialog, custom dropdown.
   Needs script.js first.
   ===================================================================== */

const ICON = {
  overview: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  projects: '<path d="M3 7h18M3 12h18M3 17h12"/>',
  money: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>',
  invoice: '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h5"/>',
  reminders: '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
  quotes: '<path d="M4 4h16v12H8l-4 4z"/>',
  payments: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  team: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c.6-3.4 3-5.2 6-5.2s5.4 1.8 6 5.2"/><path d="M16 5.2a3 3 0 0 1 0 5.6M18 14.8c1.6.7 2.6 2.4 3 5.2"/>',
};

/* view, label, section a team member needs (null = everyone, 'owner' = only you), href for real pages */
const ADMIN_NAV = [
  ['overview', 'Overview', null],
  ['projects', 'Projects', 'projects'],
  ['money', 'Pending amounts', 'money'],
  ['invoice', 'Invoice builder', 'money', '/invoice'],
  ['reminders', 'Reminders', 'reminders'],
  ['quotes', 'Quotes', 'quotes'],
  ['payments', 'Payments', 'payments'],
  ['team', 'Team', 'owner'],
];

const Admin = {
  info: null,
  can(section) {
    const i = this.info;
    if (!i) return false;
    if (section === null) return true;
    if (section === 'owner') return i.owner;
    return i.owner || i.access.includes(section);
  },
  setKey(k) { k ? localStorage.setItem('deon.adminKey', k) : localStorage.removeItem('deon.adminKey'); },

  /* Draws the sidebar into #admSide. On /admin, items switch views; elsewhere they link back. */
  sidebar(active) {
    const onAdmin = location.pathname.replace(/\/$/, '') === '/admin';
    const items = ADMIN_NAV.filter(([, , need]) => this.can(need)).map(([v, label, , href]) => {
      const url = href || (onAdmin ? '#' + v : '/admin#' + v);
      return `<a href="${url}" data-view="${v}"${v === active ? ' class="on" aria-current="page"' : ''}><svg viewBox="0 0 24 24" aria-hidden="true">${ICON[v]}</svg><span>${label}</span><span class="adm-count" data-count="${v}"></span></a>`;
    }).join('');
    const i = this.info;
    $('#admSide').innerHTML = `
      <div class="adm-brand"><a href="/admin" class="nav-logo">deon<span>.</span></a><span>Admin</span></div>
      <nav class="adm-nav" aria-label="Admin">${items}</nav>
      <div class="adm-side-foot">
        <div class="adm-me"><span class="adm-avatar">${esc(i.name.slice(0, 1).toUpperCase())}</span><div><strong>${esc(i.name)}</strong><span>${i.owner ? 'Owner' : 'Team member'}</span></div></div>
        <div class="adm-side-links">
          <span class="adm-pill${i.email ? '' : ' off'}">${i.email ? 'Email on' : 'Email off'}</span>
          ${i.owner ? '<button type="button" class="adm-link" id="testMail">Send test emails</button>' : ''}
          <a class="adm-link" href="/" target="_blank">View site</a>
          <button type="button" class="adm-link" id="lockBtn">Lock</button>
        </div>
      </div>`;
    $('#lockBtn').addEventListener('click', () => { this.setKey(''); location.href = '/admin'; });
    $('#testMail')?.addEventListener('click', async (e) => {
      e.target.disabled = true;
      try { const r = await api('/api/admin/email-test', { method: 'POST', admin: true }); toast(`Sent ${r.sent} sample emails to ${r.to}`); }
      catch (err) { toast(err.message); }
      finally { e.target.disabled = false; }
    });
  },
  mark(active) {
    $$('#admSide .adm-nav a').forEach((a) => {
      const on = a.dataset.view === active;
      a.classList.toggle('on', on);
      on ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current');
    });
  },
  count(view, n) { const c = $(`[data-count="${view}"]`); if (c) c.textContent = n || ''; },

  /* Checks the stored key. Resolves with the check info, or shows the gate and resolves null. */
  async start() {
    wakeApi();
    const gate = $('#gate'), app = $('#app');
    const tryOpen = async () => {
      try { this.info = await api('/api/admin/check', { admin: true }); }
      catch (e) {
        gate.hidden = false; app.hidden = true;
        if (localStorage.getItem('deon.adminKey')) { $('#gateMsg').textContent = e.status === 401 ? 'That key doesn\'t work.' : e.message; $('#gateMsg').hidden = false; }
        return null;
      }
      gate.hidden = true; app.hidden = false;
      return this.info;
    };
    return new Promise((resolve) => {
      $('#gateForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        this.setKey($('#a-key').value.trim());
        const btn = e.target.querySelector('button'); btn.disabled = true;
        const ok = await tryOpen(); btn.disabled = false;
        if (ok) resolve(ok);
      });
      if (localStorage.getItem('deon.adminKey')) tryOpen().then((ok) => ok && resolve(ok));
      else gate.hidden = false;
    });
  },
};

/* In-page confirm dialog. Resolves true when confirmed. */
const confirmUI = ({ title, text = '', ok = 'Confirm', danger = false }) => new Promise((resolve) => {
  const wrap = document.createElement('div');
  wrap.className = 'adm-modal';
  wrap.innerHTML = `
    <div class="adm-modal-card" role="alertdialog" aria-modal="true" aria-labelledby="mTitle" aria-describedby="mText">
      <h2 id="mTitle">${esc(title)}</h2>
      ${text ? `<p id="mText">${text}</p>` : ''}
      <div class="adm-modal-actions">
        <button type="button" class="btn btn-sm btn-outline" data-no>Cancel</button>
        <button type="button" class="btn btn-sm ${danger ? 'btn-danger' : 'btn-ink'}" data-yes>${esc(ok)}</button>
      </div>
    </div>`;
  const last = document.activeElement;
  const close = (v) => {
    wrap.classList.remove('show');
    removeEventListener('keydown', key);
    setTimeout(() => wrap.remove(), 180);
    last?.focus?.();
    resolve(v);
  };
  const key = (e) => {
    if (e.key === 'Escape') close(false);
    if (e.key === 'Tab') { // keep focus inside
      const b = $$('button', wrap), first = b[0], end = b[b.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); end.focus(); }
      else if (!e.shiftKey && document.activeElement === end) { e.preventDefault(); first.focus(); }
    }
  };
  wrap.addEventListener('click', (e) => { if (e.target === wrap || e.target.closest('[data-no]')) close(false); if (e.target.closest('[data-yes]')) close(true); });
  addEventListener('keydown', key);
  document.body.append(wrap);
  requestAnimationFrame(() => wrap.classList.add('show'));
  $(danger ? '[data-no]' : '[data-yes]', wrap).focus();
});

/* One outside-click handler for every dropdown: closes whichever is open. */
let openDropdown = null;
document.addEventListener('click', (e) => { if (openDropdown && !openDropdown.host.contains(e.target)) openDropdown.shut(); });

/* Custom dropdown. options: [{ value, label, count? }]. Returns { set(value), update(options) }. */
const dropdown = (host, { label, options, value, onChange }) => {
  host.classList.add('dd');
  host.innerHTML = `<button type="button" class="dd-btn" aria-haspopup="listbox" aria-expanded="false"><span class="dd-label">${esc(label)}</span><span class="dd-value"></span><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5L6 7.5L9 4.5"/></svg></button><ul class="dd-menu" role="listbox" tabindex="-1" hidden></ul>`;
  const btn = $('.dd-btn', host), menu = $('.dd-menu', host);
  let opts = options, cur = value, focus = 0;
  const draw = () => {
    const o = opts.find((x) => x.value === cur) || opts[0];
    $('.dd-value', host).textContent = o.label;
    menu.innerHTML = opts.map((x, i) => `<li role="option" data-v="${esc(x.value)}" aria-selected="${x.value === cur}" class="${i === focus ? 'focus' : ''}"><span>${esc(x.label)}</span>${x.count != null ? `<em>${x.count}</em>` : ''}<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 6.2l2.3 2.3 4.7-5"/></svg></li>`).join('');
  };
  const isOpen = () => !menu.hidden;
  const open = () => { if (openDropdown) openDropdown.shut(); openDropdown = { host, shut }; focus = Math.max(0, opts.findIndex((x) => x.value === cur)); draw(); menu.hidden = false; btn.setAttribute('aria-expanded', 'true'); host.classList.add('open'); menu.focus(); };
  const shut = (refocus) => { if (openDropdown?.host === host) openDropdown = null; menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); host.classList.remove('open'); if (refocus) btn.focus(); };
  const pick = (v) => { shut(true); if (v !== cur) { cur = v; draw(); onChange(v); } };
  btn.addEventListener('click', () => isOpen() ? shut() : open());
  menu.addEventListener('click', (e) => { const li = e.target.closest('li'); if (li) pick(li.dataset.v); });
  menu.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); focus = (focus + (e.key === 'ArrowDown' ? 1 : -1) + opts.length) % opts.length; draw(); }
    else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(opts[focus].value); }
    else if (e.key === 'Escape' || e.key === 'Tab') shut(e.key === 'Escape');
  });
  draw();
  return {
    set(v) { cur = v; draw(); },
    update(o) { opts = o; draw(); },
    get value() { return cur; },
  };
};
