/* THINGBESIDE — interactions (vanilla, no dependencies) */
(() => {
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => [...c.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const ease = t => 1 - Math.pow(1 - t, 3);
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };

  /* ---------- Split text into words ---------- */
  $$('[data-split]').forEach(el => {
    let i = 0;
    const walk = node => {
      [...node.childNodes].forEach(n => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach(part => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.append(' '); return; }
            const w = document.createElement('span'); w.className = 'w';
            const inner = document.createElement('span'); inner.textContent = part;
            inner.style.setProperty('--i', i++); w.append(inner); frag.append(w);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1) walk(n);
      });
    };
    walk(el);
  });

  /* ---------- Intro curtain ---------- */
  const intro = $('.intro');
  $$('.intro__word span').forEach((s, k) => s.style.setProperty('--k', k));
  const startPage = () => {
    document.body.classList.remove('is-loading');
    $$('.hero [data-split]').forEach(el => el.classList.add('in'));
    heroIntro();
  };
  if (reduce || !intro) { intro && intro.classList.add('gone'); startPage(); }
  else {
    const cnt = $('.intro__count'); const t0 = performance.now(); const dur = 1100;
    const tick = now => {
      const p = clamp((now - t0) / dur);
      cnt.textContent = String(Math.round(ease(p) * 100)).padStart(3, '0');
      if (p < 1) requestAnimationFrame(tick);
      else {
        intro.classList.add('out'); setTimeout(startPage, 250);
        setTimeout(() => intro.classList.add('gone'), 1100);
      }
    };
    requestAnimationFrame(tick);
  }

  /* ---------- Reveal on scroll ---------- */
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      e.target.classList.add('in'); io.unobserve(e.target);
    });
  }, { rootMargin: '0px 0px -12% 0px' });
  $$('[data-reveal], [data-split]').forEach(el => { if (!el.closest('.hero')) io.observe(el); });
  // stagger groups
  ['.stats', '.plans', '.facts', '.faq__list', '.work__list', '.finder__q'].forEach(sel => {
    const g = $(sel); if (!g) return;
    $$('[data-reveal]', g).forEach((el, i) => el.style.setProperty('--d', `${i * 80}ms`));
  });
  const aboutFig = $('.about__fig');

  /* ---------- Count-up numbers ---------- */
  const fmt = n => n.toLocaleString('en-AU');
  const countIO = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      countIO.unobserve(e.target);
      const el = e.target, to = +el.dataset.count;
      if (reduce) { el.textContent = fmt(to); return; }
      const t0 = performance.now(), dur = 1500;
      const step = now => {
        const p = clamp((now - t0) / dur);
        el.textContent = fmt(Math.round(ease(p) * to));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }, { threshold: .6 });
  $$('[data-count]').forEach(el => countIO.observe(el));

  /* ---------- Cursor ---------- */
  const cur = $('.cursor'), curLabel = $('.cursor__label');
  let mx = innerWidth / 2, my = innerHeight / 2, cx = mx, cy = my;
  if (fine) {
    addEventListener('pointermove', e => { mx = e.clientX; my = e.clientY; }, { passive: true });
    document.addEventListener('pointerover', e => {
      const t = e.target.closest('[data-cursor], a, button');
      cur.classList.remove('is-big', 'is-link');
      cur.classList.toggle('is-hero', !!e.target.closest('.hero') && !e.target.closest('a, button'));
      if (!t) return;
      if (t.dataset.cursor && !t.closest('.hero')) { curLabel.textContent = t.dataset.cursor; cur.classList.add('is-big'); }
      else if (t.matches('a, button')) cur.classList.add('is-link');
    });
    document.addEventListener('pointerleave', () => cur.classList.add('is-hidden'));
    document.addEventListener('pointerenter', () => cur.classList.remove('is-hidden'));
  }

  /* ---------- Hero spotlight ---------- */
  const hero = $('.hero'), coords = $('.hero__coords');
  let hx = .7, hy = .55, hr = 0, tr = 0, hTx = .7, hTy = .55, heroActive = false, heroAuto = !fine;
  function heroIntro() { heroActive = true; tr = fine ? 0 : Math.min(130, innerWidth * .3); if (fine) setTimeout(() => { if (tr === 0) tr = 130; }, 400); }
  if (fine) {
    hero.addEventListener('pointermove', e => {
      const b = hero.getBoundingClientRect();
      hTx = (e.clientX - b.left) / b.width; hTy = (e.clientY - b.top) / b.height; tr = 190;
      if (coords) coords.textContent = `X ${String(Math.round(e.clientX)).padStart(3, '0')} · Y ${String(Math.round(e.clientY - b.top)).padStart(3, '0')}`;
    });
    hero.addEventListener('pointerleave', () => { tr = 0; });
    hero.addEventListener('pointerdown', () => { tr = 320; });
    hero.addEventListener('pointerup', () => { tr = 190; });
  } else {
    hero.addEventListener('touchmove', e => {
      const b = hero.getBoundingClientRect(), t = e.touches[0];
      hTx = (t.clientX - b.left) / b.width; hTy = (t.clientY - b.top) / b.height; heroAuto = false;
      clearTimeout(hero._t); hero._t = setTimeout(() => heroAuto = true, 2000);
    }, { passive: true });
  }

  /* ---------- Build story ---------- */
  const build = $('#build');
  const stack = $('.stack');
  const layers = $$('.layer', stack);
  const copy = $('.build__copy');
  const stepEl = $('.build__step');
  const rulerFill = $('.ruler__fill');
  const rulerLis = $$('.ruler__labels li');
  const dayEl = $('.ruler__day b');
  const steps = [
    { when: 'Day 1 · 15 min', name: 'Discovery call', text: 'A free, no-pressure chat about your business, your customers and what your website needs to do. If we’re a good fit, you get a fixed quote and timeline.' },
    { when: 'Days 2–4', name: 'Brief', text: 'You fill in a simple brief covering your services, style and examples you like. Don’t have everything? I’ll help fill the gaps and write or polish your content.' },
    { when: 'Weeks 1–2', name: 'Design', text: 'I design your homepage first so you see the look and feel early. Once you’re happy, I design the remaining pages. Two rounds of revisions included.' },
    { when: 'Weeks 2–3', name: 'Build', text: 'I build your site in Framer with smooth animations, mobile-friendly layouts and SEO basics. You get a private preview link to check it on your own phone.' },
    { when: 'Week 3', name: 'Launch & support', text: 'I connect your domain, run final checks and put your site live. You get a walkthrough on editing it yourself, plus 14 days of free support.' }
  ];
  let curStep = -1, sx = 0, sy = 0, tsx = 0, tsy = 0;
  if (fine) addEventListener('pointermove', e => { tsx = e.clientX / innerWidth - .5; tsy = e.clientY / innerHeight - .5; }, { passive: true });

  const setStep = s => {
    if (s === curStep) return;
    const first = curStep === -1; curStep = s;
    stepEl.textContent = `Stage ${String(s + 1).padStart(2, '0')}`;
    rulerLis.forEach((li, i) => { li.classList.toggle('is-on', i < s); li.classList.toggle('is-now', i === s); });
    const apply = () => {
      $('.build__when', copy).textContent = steps[s].when;
      $('.build__name', copy).textContent = steps[s].name;
      $('.build__text', copy).textContent = steps[s].text;
    };
    if (first || reduce) { apply(); return; }
    copy.classList.add('swap');
    clearTimeout(copy._t);
    copy._t = setTimeout(() => { apply(); copy.classList.remove('swap'); }, 260);
  };

  const renderBuild = () => {
    const b = build.getBoundingClientRect();
    const total = b.height - innerHeight;
    const p = clamp(-b.top / total);
    const mobile = innerWidth < 600;
    const SEG = .16; // 5 stages: 0 – .80, then flatten
    const s = Math.min(4, Math.floor(p / SEG));
    setStep(s);
    const flat = smooth(.8, .95, p);
    const gap = (mobile ? 34 : 64) * (1 - flat);
    sx = lerp(sx, tsx, .08); sy = lerp(sy, tsy, .08);
    const rx = 58 * (1 - flat) - sy * 10 * (1 - flat * .7);
    const rz = -36 * (1 - flat) + sx * 10 * (1 - flat * .7);
    const sc = lerp(mobile ? .72 : .74, 1, flat);
    stack.style.setProperty('--rx', `${rx}deg`);
    stack.style.setProperty('--rz', `${rz}deg`);
    stack.style.setProperty('--s', sc);
    layers.forEach((L, i) => {
      if (i === 5) { L.style.setProperty('--o', smooth(.86, .96, p)); L.style.setProperty('--z', `${5 * gap + 2}px`); return; }
      const e = ease(clamp((p - i * SEG + .02) / .09));
      const z = i * gap + (1 - e) * 260;
      L.style.setProperty('--z', `${z}px`);
      L.style.setProperty('--o', i === 0 ? Math.max(e, .9 * clamp(p / .01)) || e : e);
      L.classList.toggle('is-active', i === s && flat < .3);
    });
    rulerFill.style.setProperty('--p', clamp(p / .95));
    const days = [1, 3, 8, 14, 21];
    const local = clamp((p - s * SEG) / SEG);
    const day = s < 4 ? Math.round(lerp(days[s], days[s + 1], local)) : 21;
    dayEl.textContent = String(day).padStart(2, '0');
  };

  /* ---------- Auto-play ("Watch a site get built") ---------- */
  let auto = null;
  const stopAuto = () => { if (auto) { cancelAnimationFrame(auto.raf); auto = null; document.documentElement.style.scrollBehavior = ''; } };
  $$('[data-autoplay]').forEach(btn => btn.addEventListener('click', () => {
    stopAuto();
    document.documentElement.style.scrollBehavior = 'auto';
    const start = scrollY, top = build.offsetTop, end = top + build.offsetHeight - innerHeight;
    if (reduce) { scrollTo(0, top); return; }
    const t0 = performance.now(), d1 = 900, d2 = 9000;
    auto = {};
    const step = now => {
      const t = now - t0;
      if (t < d1) scrollTo(0, lerp(start, top, ease(t / d1)));
      else { const q = clamp((t - d1) / d2); scrollTo(0, lerp(top, end, q < .5 ? 2 * q * q : 1 - Math.pow(-2 * q + 2, 2) / 2)); if (q >= 1) return stopAuto(); }
      auto.raf = requestAnimationFrame(step);
    };
    auto.raf = requestAnimationFrame(step);
  }));
  ['wheel', 'touchstart', 'keydown', 'pointerdown'].forEach(ev => addEventListener(ev, e => {
    if (ev === 'pointerdown' && e.target.closest('[data-autoplay]')) return;
    stopAuto();
  }, { passive: true }));

  /* ---------- Work preview follows cursor ---------- */
  const preview = $('.preview'), pImg = $('img', preview);
  let px = 0, py = 0, pvx = 0, pRot = 0;
  if (fine) {
    $$('.work__row').forEach(row => {
      row.addEventListener('pointerenter', () => { pImg.src = row.dataset.img; preview.classList.add('is-on'); preview.style.transform = 'scale(1)'; });
      row.addEventListener('pointerleave', () => { preview.classList.remove('is-on'); preview.style.transform = 'scale(.6)'; });
    });
  }

  /* ---------- Services ---------- */
  const svcItems = $$('.svc__item'), svcImgs = $$('.svc__fig img'), svcIdx = $('.svc__idx');
  const setSvc = i => {
    svcItems.forEach((b, k) => { b.classList.toggle('is-on', k === i); b.setAttribute('aria-expanded', k === i); });
    svcImgs.forEach((im, k) => im.classList.toggle('is-on', k === i));
    svcIdx.textContent = String(i + 1).padStart(2, '0');
  };
  svcItems.forEach(b => {
    b.addEventListener('click', () => setSvc(+b.dataset.i));
    if (fine) b.addEventListener('pointerenter', () => setSvc(+b.dataset.i));
  });

  /* ---------- Finder ---------- */
  const state = { start: 'new', size: 'few' };
  const pagesEl = $('.pages'), result = $('.result');
  const R = {
    one: { for: 'For new businesses', name: 'One-Page Website', price: 390, unit: 'AUD', time: 'Live within a week', pages: 1 },
    few: { for: 'For growing businesses', name: 'Business Website', price: 1290, unit: 'AUD', time: 'Most sites live in about 3 weeks', pages: 6 },
    lots: { for: 'For businesses with plenty to say', name: 'Large Website', price: 2490, unit: 'AUD', time: 'Fixed quote after a free call', pages: 10 },
    slow: { for: 'For slow or clunky sites', name: 'Website Rebuild', price: 990, unit: 'AUD', time: 'Keep your Google rankings', pages: 'rebuild' },
    edit: { for: 'For live websites', name: 'Updates & Changes', price: 75, unit: '/hour', time: 'Most updates take under two hours', pages: 'edit' }
  };
  for (let i = 0; i < 10; i++) {
    const d = document.createElement('div'); d.className = 'pg';
    d.innerHTML = '<i></i><i></i><i></i><i></i><i></i>'; pagesEl.append(d);
  }
  const pgs = $$('.pg', pagesEl);
  const tag = document.createElement('span'); tag.className = 'pages__tag mono'; pagesEl.append(tag);
  let shownPrice = 1290;
  const animatePrice = to => {
    const el = $('.result__num'), from = shownPrice; shownPrice = to;
    if (reduce) { el.textContent = fmt(to); return; }
    const t0 = performance.now();
    const st = now => { const p = clamp((now - t0) / 700); el.textContent = fmt(Math.round(lerp(from, to, ease(p)))); if (p < 1) requestAnimationFrame(st); };
    requestAnimationFrame(st);
  };
  const updateFinder = (first) => {
    const key = state.start === 'new' ? state.size : state.start;
    const r = R[key];
    $('[data-q="size"]').style.opacity = state.start === 'new' ? 1 : .35;
    const write = () => {
      $('.result__for').textContent = r.for;
      $('.result__name').textContent = r.name;
      $('.result__price .aud').textContent = r.unit;
      $('.result__time').textContent = r.time;
    };
    if (first) write(); else { result.classList.add('swap'); setTimeout(() => { write(); result.classList.remove('swap'); }, 200); }
    animatePrice(r.price);
    // page stack visual
    const n = typeof r.pages === 'number' ? r.pages : 2;
    const spread = innerWidth < 600 ? 16 : 22;
    pgs.forEach((pg, i) => {
      pg.className = 'pg';
      if (i >= n) { pg.classList.add('is-out'); pg.style.transform = 'translateY(30px) scale(.9)'; return; }
      if (r.pages === 'rebuild') {
        pg.style.transform = i === 0 ? 'translateX(-70px) rotateY(18deg) scale(.92)' : 'translateX(70px) rotateY(-18deg)';
        if (i === 0) pg.classList.add('is-old'); else pg.classList.add('is-front');
      } else if (r.pages === 'edit') {
        pg.style.transform = i === 0 ? 'translateX(-10px) rotate(-4deg)' : 'translateX(10px) rotate(3deg)';
        if (i === 1) pg.classList.add('is-front');
      } else {
        const c = (i - (n - 1) / 2);
        pg.style.transform = `translateX(${c * spread}px) translateZ(${-Math.abs(c) * 20}px) rotateY(${c * -6}deg)`;
        pg.style.zIndex = 20 - Math.abs(Math.round(c));
        if (Math.abs(c) < .6 || n === 1) pg.classList.add('is-front');
      }
    });
    tag.textContent = r.pages === 'rebuild' ? 'Old → New' : r.pages === 'edit' ? 'Edits' : `${r.pages === 10 ? '10+' : r.pages === 6 ? '5–10' : 1} page${n > 1 ? 's' : ''}`;
  };
  $$('.q').forEach(q => {
    $$('.pick', q).forEach(b => b.addEventListener('click', () => {
      $$('.pick', q).forEach(x => { x.classList.toggle('is-on', x === b); x.setAttribute('aria-pressed', x === b); });
      state[q.dataset.q] = b.dataset.v;
      updateFinder();
    }));
    $$('.pick', q).forEach(x => x.setAttribute('aria-pressed', x.classList.contains('is-on')));
  });
  updateFinder(true);

  /* ---------- FAQ ---------- */
  $$('.qa').forEach(qa => {
    const b = $('button', qa);
    b.addEventListener('click', () => {
      const open = !qa.classList.contains('is-open');
      $$('.qa').forEach(o => { o.classList.remove('is-open'); $('button', o).setAttribute('aria-expanded', 'false'); });
      qa.classList.toggle('is-open', open); b.setAttribute('aria-expanded', open);
    });
  });

  /* ---------- Copy email ---------- */
  const toast = $('.toast');
  const showToast = msg => { toast.textContent = msg; toast.classList.add('is-on'); clearTimeout(toast._t); toast._t = setTimeout(() => toast.classList.remove('is-on'), 1800); };
  $$('[data-copy]').forEach(b => b.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(b.dataset.copy); showToast('Email copied ✓'); }
    catch { location.href = `mailto:${b.dataset.copy}`; }
  }));

  /* ---------- Magnetic buttons ---------- */
  if (fine && !reduce) $$('.magnet').forEach(m => {
    m.addEventListener('pointermove', e => {
      const r = m.getBoundingClientRect();
      m.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * .25}px, ${(e.clientY - r.top - r.height / 2) * .35}px)`;
    });
    m.addEventListener('pointerleave', () => { m.style.transform = ''; });
  });

  /* ---------- Menu ---------- */
  const burger = $('.nav__burger'), menu = $('#menu');
  const setMenu = open => {
    document.body.classList.toggle('menu-open', open);
    burger.setAttribute('aria-expanded', open); menu.setAttribute('aria-hidden', !open);
    document.body.style.overflow = open ? 'hidden' : '';
  };
  burger.addEventListener('click', () => setMenu(!document.body.classList.contains('menu-open')));
  $$('a', menu).forEach(a => a.addEventListener('click', () => setMenu(false)));
  addEventListener('keydown', e => { if (e.key === 'Escape') setMenu(false); });

  /* ---------- Nav hide/show, active link, sticky CTA ---------- */
  const nav = $('#nav'), sticky = $('.sticky-cta'), contact = $('#contact');
  let lastY = scrollY;
  const navLinks = $$('.nav__links a');
  const secs = navLinks.map(a => $(a.getAttribute('href')));
  const onScroll = () => {
    const y = scrollY;
    nav.classList.toggle('is-hidden', y > lastY && y > 400 && !document.body.classList.contains('menu-open'));
    lastY = y;
    const cTop = contact.getBoundingClientRect().top;
    const bR = build.getBoundingClientRect();
    const inBuild = bR.top < innerHeight * .5 && bR.bottom > innerHeight * .5;
    const on = y > innerHeight * .9 && cTop > innerHeight * .8 && !inBuild;
    sticky.classList.toggle('is-on', on);
    sticky.setAttribute('aria-hidden', !on);
    $('a', sticky).tabIndex = on ? 0 : -1;
    let active = -1;
    secs.forEach((s, i) => { if (s && s.getBoundingClientRect().top < innerHeight * .4) active = i; });
    navLinks.forEach((a, i) => a.classList.toggle('is-on', i === active));
  };
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- Footer clock & wordmark ---------- */
  const clock = $('.foot__clock');
  const tickClock = () => { clock.textContent = new Intl.DateTimeFormat('en-AU', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Australia/Brisbane' }).format(new Date()); };
  tickClock(); setInterval(tickClock, 15000);
  const fw = $$('.foot__word span'), foot = $('.foot'), fwEl = $('.foot__word');
  const fitWord = () => {
    fwEl.style.setProperty('--fw', '100px');
    const natural = fw.reduce((a, s) => a + s.getBoundingClientRect().width, 0);
    const avail = fwEl.clientWidth;
    fwEl.style.setProperty('--fw', `${Math.floor(100 * avail / natural * .98)}px`);
  };
  fitWord(); addEventListener('resize', fitWord);
  document.fonts && document.fonts.ready.then(fitWord);

  /* ---------- Main loop ---------- */
  const loop = () => {
    // cursor
    if (fine) { cx = lerp(cx, mx, .2); cy = lerp(cy, my, .2); cur.style.transform = `translate(${cx}px, ${cy}px)`; }
    // hero
    if (heroActive) {
      const hb = hero.getBoundingClientRect();
      if (hb.bottom > 0) {
        if (heroAuto) { const t = performance.now() / 1000; hTx = .5 + Math.sin(t * .6) * .3; hTy = .5 + Math.sin(t * .9) * .22; }
        hx = lerp(hx, hTx, .09); hy = lerp(hy, hTy, .09); hr = lerp(hr, tr, .08);
        hero.style.setProperty('--x', `${hx * 100}%`); hero.style.setProperty('--y', `${hy * 100}%`); hero.style.setProperty('--r', `${hr}px`);
      }
    }
    // preview
    if (fine && preview.classList.contains('is-on')) {
      const nx = lerp(px, mx, .14); pvx = nx - px; px = nx; py = lerp(py, my, .14);
      pRot = lerp(pRot, clamp(pvx * .6, -12, 12), .1);
      preview.style.left = `${px}px`; preview.style.top = `${py}px`;
      preview.style.rotate = `${pRot}deg`;
    } else { px = mx; py = my; }
    // build
    const bb = build.getBoundingClientRect();
    if (bb.top < innerHeight && bb.bottom > 0) renderBuild();
    // footer wordmark
    const fb = foot.getBoundingClientRect();
    if (fb.top < innerHeight) {
      const q = clamp((innerHeight - fb.top) / fb.height);
      fw.forEach((s, i) => s.style.setProperty('--fy', ((1 - ease(clamp(q * 1.6 - i * .04))) * 60).toFixed(2)));
    }
    requestAnimationFrame(loop);
  };
  renderBuild();
  requestAnimationFrame(loop);

  // About image zoom when revealed
  if (aboutFig) new IntersectionObserver((es, o) => es.forEach(e => { if (e.isIntersecting) { aboutFig.classList.add('in'); o.disconnect(); } }), { threshold: .3 }).observe(aboutFig);
})();
