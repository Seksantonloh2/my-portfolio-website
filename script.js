(function () {
  document.documentElement.classList.add("js");

  const header = document.querySelector(".site-header");
  const nav = document.getElementById("nav");
  const toggle = document.querySelector(".nav-toggle");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Header shadow on scroll
  const onScroll = () => header.classList.toggle("scrolled", window.scrollY > 8);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  // Mobile menu
  const setMenu = (open) => {
    nav.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  };
  toggle.addEventListener("click", () => setMenu(!nav.classList.contains("open")));
  nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => setMenu(false)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setMenu(false); });

  // Highlight the nav link for the section in view
  const links = [...nav.querySelectorAll("ul a")];
  const sections = links.map((a) => document.querySelector(a.getAttribute("href"))).filter(Boolean);
  if ("IntersectionObserver" in window) {
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#" + entry.target.id));
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach((s) => spy.observe(s));
  }

  // Scroll reveal
  const reveals = document.querySelectorAll(".reveal");
  if (reduceMotion || !("IntersectionObserver" in window)) {
    reveals.forEach((el) => el.classList.add("in"));
  } else {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const siblings = [...entry.target.parentElement.children];
        entry.target.style.transitionDelay = siblings.indexOf(entry.target) * 80 + "ms";
        entry.target.classList.add("in");
        io.unobserve(entry.target);
      });
    }, { threshold: 0.15 });
    reveals.forEach((el) => io.observe(el));
  }

  // Animated counters
  const counters = document.querySelectorAll("[data-count]");
  const format = (el, value) => {
    const decimals = Number(el.dataset.decimals || 0);
    el.textContent = (el.dataset.prefix || "") + value.toFixed(decimals) + (el.dataset.suffix || "");
  };
  if (!reduceMotion && "IntersectionObserver" in window) {
    const countIO = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const target = Number(el.dataset.count);
        const start = performance.now();
        const duration = 1600;
        const tick = (now) => {
          const p = Math.min((now - start) / duration, 1);
          format(el, target * (1 - Math.pow(1 - p, 3)));
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
        countIO.unobserve(el);
      });
    }, { threshold: 0.5 });
    counters.forEach((el) => { format(el, 0); countIO.observe(el); });
  }

  // Contact form (front-end validation only — wire to your backend or form service)
  const form = document.getElementById("contact-form");
  const status = document.getElementById("form-status");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    let valid = true;
    form.querySelectorAll("[required]").forEach((input) => {
      const ok = input.type === "email" ? /^\S+@\S+\.\S+$/.test(input.value) : input.value.trim() !== "";
      input.closest(".field").classList.toggle("invalid", !ok);
      if (!ok) valid = false;
    });
    status.className = "form-status " + (valid ? "success" : "error");
    status.textContent = valid
      ? "Thank you — a partner will be in touch within one business day."
      : "Please add your name and a valid work email.";
    if (valid) form.reset();
  });

  document.getElementById("year").textContent = new Date().getFullYear();
})();
