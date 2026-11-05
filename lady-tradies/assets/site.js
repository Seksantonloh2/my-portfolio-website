/* Lady Tradies — shared site script (header/footer, motion, page transitions, illustrations) */
(() => {
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = t => 1 - Math.pow(1 - t, 3);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const ARROW = '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 6h8M6.5 2.5 10 6l-3.5 3.5"/></svg>';
const MARK = '<svg class="logo-mark" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="16" fill="#FD37D6"/><path d="M10 29.5 32 11.5l22 18M18.5 33.5v18h10.5M33.5 37h13.5M40.25 37v14.5" fill="none" stroke="#191919" stroke-width="5.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const btn = (href, label, cls = 'btn-accent', arrow = true) =>
  `<a href="${href}" class="btn ${cls}"><span class="lbl"><span>${label}</span><span>${label}</span></span>${arrow ? `<span class="arr" aria-hidden="true">${ARROW}</span>` : ''}</a>`;

/* ---------- Header + footer ---------- */
const page = document.body.dataset.page || 'home';
const NAV = [
  ['directory.html', 'Find a tradie', 'directory'],
  ['index.html#how', 'How it works', ''],
  ['index.html#start', 'Getting started', ''],
  ['join.html', 'List your business', 'join'],
  ['about.html', 'About', 'about'],
  ['contact.html', 'Contact', 'contact'],
];
const hdrSlot = $('#site-header');
if (hdrSlot) hdrSlot.outerHTML = `
<header class="hdr" id="hdr">
  <div class="wrap">
    <a href="index.html" class="logo" aria-label="Lady Tradies Australia home">${MARK}Lady Tradies</a>
    <nav class="nav" aria-label="Main">${NAV.map(([h, l, k]) => `<a href="${h}"${k === page ? ' aria-current="page"' : ''}>${l}</a>`).join('')}</nav>
    <div class="hdr-ctas">
      ${btn('directory.html', 'Find a tradie')}
      <button class="menu-btn" id="menu-btn" aria-expanded="false" aria-controls="mnav" aria-label="Open menu"><i></i><i></i></button>
    </div>
  </div>
  <nav class="mnav" id="mnav" aria-label="Mobile">${NAV.map(([h, l, k]) => `<a href="${h}"${k === page ? ' aria-current="page"' : ''}>${l}<span aria-hidden="true">${ARROW}</span></a>`).join('')}</nav>
</header>`;
const ftrSlot = $('#site-footer');
if (ftrSlot) ftrSlot.outerHTML = `
<footer class="ftr tint">
  <div class="wrap">
    <div>
      <a href="index.html" class="logo">${MARK}Lady Tradies</a>
      <p style="margin-top:16px;max-width:34ch">Helping Australians find women in trades since 2012.</p>
    </div>
    <div><h4>Directory</h4><ul><li><a href="directory.html">Find a tradie</a></li><li><a href="join.html">List your business</a></li><li><a href="index.html#how">How it works</a></li></ul></div>
    <div><h4>Women in trades</h4><ul><li><a href="index.html#start">Getting started</a></li><li><a href="about.html">Our story</a></li><li><a href="index.html#faq">FAQ</a></li></ul></div>
    <div><h4>Contact</h4><ul><li><a href="contact.html">Send us a message</a></li><li>Australia-wide</li><li>Online directory</li></ul></div>
    <div class="legal"><span>© 2026 Lady Tradies Australia · ABN to be confirmed</span><span>Demo site by THINGBESIDE · all listings shown are sample data</span></div>
  </div>
</footer>`;

const hdr = $('#hdr');
if (hdr) {
  const onScroll = () => hdr.classList.toggle('solid', scrollY > 20 || page !== 'home');
  addEventListener('scroll', onScroll, { passive: true }); onScroll();
  const mb = $('#menu-btn'), mn = $('#mnav');
  mb.addEventListener('click', () => {
    const open = mb.getAttribute('aria-expanded') !== 'true';
    mb.setAttribute('aria-expanded', open); mn.classList.toggle('open', open); hdr.classList.toggle('menu-open', open);
  });
  $$('a', mn).forEach(a => a.addEventListener('click', () => { mb.setAttribute('aria-expanded', 'false'); mn.classList.remove('open'); hdr.classList.remove('menu-open'); }));
}

/* ---------- Blur-in word splitting ---------- */
function split(el) {
  let i = 0;
  const walk = node => {
    [...node.childNodes].forEach(n => {
      if (n.nodeType === 3) {
        const frag = document.createDocumentFragment();
        n.textContent.split(/(\s+)/).forEach(part => {
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.append(part); return; }
          const s = document.createElement('span');
          s.className = 'w'; s.style.setProperty('--i', i++); s.textContent = part;
          frag.append(s);
        });
        n.replaceWith(frag);
      } else if (n.nodeType === 1) {
        if (n.matches('em')) { n.classList.add('w'); n.style.setProperty('--i', i++); }
        else walk(n);
      }
    });
  };
  walk(el);
}

/* ---------- Reveal on scroll ---------- */
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
}), { threshold: .12, rootMargin: '0px 0px -40px 0px' });
function animate(root = document) {
  $$('[data-split]', root).forEach(el => { if (!el.dataset.splitDone) { split(el); el.dataset.splitDone = 1; } });
  $$('.reveal, .blur-in', root).forEach(el => io.observe(el));
  $$('[data-count]', root).forEach(el => { if (!RM) el.textContent = '0'; cio.observe(el); });
}

/* ---------- Count-up ---------- */
const fmt = n => n.toLocaleString('en-AU', { maximumFractionDigits: 1, minimumFractionDigits: String(n).includes('.') ? 1 : 0 });
const cio = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  cio.unobserve(e.target);
  const el = e.target, to = +el.dataset.count, dec = el.dataset.count.includes('.');
  const show = v => el.textContent = dec ? v.toFixed(1) : fmt(Math.round(v));
  if (RM) { show(to); return; }
  const t0 = performance.now(), dur = 1500;
  const tick = t => { const p = clamp((t - t0) / dur); show(to * ease(p)); if (p < 1) requestAnimationFrame(tick); };
  show(0); requestAnimationFrame(tick);
}), { threshold: .6 });

/* ---------- Page transitions (between pages only; in-page anchors just smooth-scroll) ---------- */
document.addEventListener('click', e => {
  const a = e.target.closest('a[href]');
  if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || a.target === '_blank') return;
  const url = new URL(a.getAttribute('href'), location.href);
  if (url.origin !== location.origin && location.protocol !== 'file:') return;
  if (url.pathname === location.pathname) return;             // same page → native smooth scroll
  if (!/\.html$|\/$/.test(url.pathname)) return;
  e.preventDefault();
  try { sessionStorage.setItem('lt-q:' + url.pathname.split('/').pop(), url.search); } catch (_) {}
  if (RM) { location.href = url.href; return; }
  document.body.classList.add('leaving');
  setTimeout(() => location.href = url.href, 420);
});
addEventListener('pageshow', ev => { if (ev.persisted) document.body.classList.remove('leaving'); });

/* ---------- Postcode → state ---------- */
function stateOf(pc) {
  const n = +pc;
  if (!/^\d{4}$/.test(String(pc))) return null;
  if ((n >= 2600 && n <= 2618) || (n >= 2900 && n <= 2920)) return 'ACT';
  if (n >= 2000 && n <= 2999) return 'NSW';
  if (n >= 3000 && n <= 3999) return 'VIC';
  if (n >= 4000 && n <= 4999) return 'QLD';
  if (n >= 5000 && n <= 5999) return 'SA';
  if (n >= 6000 && n <= 6999) return 'WA';
  if (n >= 7000 && n <= 7999) return 'TAS';
  if (n >= 800 && n <= 999) return 'NT';
  return null;
}

/* ---------- Trade line illustrations (stand in for real photos) ---------- */
const ILL = {
  Carpenter: '<path d="M60 150 150 60"/><path d="M138 48l30 30-14 14-30-30z"/><path d="M40 170h120"/><path d="M52 170v-22h96v22"/><path d="M70 148v22M90 148v22M110 148v22M130 148v22"/>',
  Electrician: '<path d="M100 30v30"/><path d="M80 60h40l-6 44H86z"/><path d="M92 104v18h16v-18"/><path d="M100 122c0 30-40 20-40 50"/><path d="M128 70l18-14M134 90h22M128 110l18 14"/><path d="M152 150l-16 26h14l-14 22"/>',
  Plumber: '<path d="M40 70h70v30H70v80"/><path d="M110 60v50"/><path d="M90 60h40"/><path d="M110 85h40a10 10 0 0 1 10 10v20"/><path d="M160 135v6M160 152v6M160 169v6"/><circle cx="70" cy="180" r="6"/>',
  Painter: '<rect x="46" y="44" width="96" height="40" rx="8"/><path d="M142 64h14v40H100v20"/><rect x="92" y="124" width="16" height="56" rx="6"/><path d="M50 84v20M70 84v34M90 84v14"/>',
  Tiler: '<rect x="40" y="40" width="120" height="120" rx="6"/><path d="M80 40v120M120 40v120M40 80h120M40 120h120"/><path d="M130 168l26-26 14 14-26 26z"/>',
  Landscaper: '<path d="M100 180V90"/><path d="M100 120c-30 0-46-20-46-50 30 0 46 20 46 50z"/><path d="M100 104c0-30 16-50 46-50 0 30-16 50-46 50z"/><path d="M30 180h140"/><path d="M50 180c4-14 16-22 30-22M120 158c14 0 26 8 30 22"/>',
  Builder: '<path d="M40 100 100 50l60 50"/><path d="M56 88v82h88V88"/><path d="M86 170v-40h28v40"/><path d="M30 170h140"/><path d="M150 40v40M140 50h20"/>',
  Handywoman: '<rect x="40" y="96" width="120" height="70" rx="8"/><path d="M78 96V80a8 8 0 0 1 8-8h28a8 8 0 0 1 8 8v16"/><path d="M40 126h120"/><path d="M92 120h16v14H92z"/>',
};
function illus(trade, variant = 0, label = '') {
  const v = variant % 3, rot = [0, -8, 6][v], sc = [1, .86, .92][v];
  return `<div class="ill v${v}" role="img" aria-label="${esc(label || trade + ' illustration')}"><svg viewBox="0 0 200 200" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><g transform="rotate(${rot} 100 100) translate(${100 - 100 * sc} ${100 - 100 * sc}) scale(${sc})">${ILL[trade] || ILL.Builder}</g></svg>${label ? `<span>${esc(label)}</span>` : ''}</div>`;
}
const initials = n => n.split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();

function params() {
  let q = location.search;
  if (!q) { try { q = sessionStorage.getItem('lt-q:' + location.pathname.split('/').pop()) || ''; } catch (_) {} }
  return new URLSearchParams(q);
}
function go(href) {
  const url = new URL(href, location.href);
  try { sessionStorage.setItem('lt-q:' + url.pathname.split('/').pop(), url.search); } catch (_) {}
  if (RM) { location.href = url.href; return; }
  document.body.classList.add('leaving');
  setTimeout(() => location.href = url.href, 420);
}
window.LT = { params, go, RM, $, $$, clamp, ease, esc, btn, ARROW, MARK, animate, stateOf, illus, initials };
animate();
// hero content shows immediately
requestAnimationFrame(() => $$('.hero .blur-in, .hero .reveal, .page-hero .blur-in, .page-hero .reveal').forEach(el => el.classList.add('in')));
})();
