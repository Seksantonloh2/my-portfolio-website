"""Render web pages in a real browser and extract design data from them.

For each page we scroll through the whole document (so lazy content and scroll
animations load), take a few screenshots, and collect:
text, headings, links, fonts, colors, animation libraries, CSS keyframes,
transitions, hover effects, and other interaction signals.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field

from playwright.sync_api import Browser, sync_playwright

VIEWPORT = {"width": 1440, "height": 900}
MAX_TEXT_CHARS = 30000
MAX_SCREENSHOTS = 4

# Runs inside the page and returns everything we know how to measure.
EXTRACT_JS = r"""
() => {
  const uniq = (a) => [...new Set(a)];
  const count = (arr) => {
    const m = {};
    arr.forEach((x) => { if (x) m[x] = (m[x] || 0) + 1; });
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  };
  const els = [...document.querySelectorAll("body *")].slice(0, 4000);
  const styles = els.map((e) => [e, getComputedStyle(e)]);

  const colors = count(styles.flatMap(([, s]) => [s.color, s.backgroundColor])
    .filter((c) => c && c !== "rgba(0, 0, 0, 0)" && c !== "transparent")).slice(0, 16);
  const fonts = count(styles.map(([, s]) => s.fontFamily)).slice(0, 8);
  const pick = (sel) => {
    const e = document.querySelector(sel);
    if (!e) return null;
    const s = getComputedStyle(e);
    return { font: s.fontFamily, size: s.fontSize, weight: s.fontWeight, lineHeight: s.lineHeight,
             letterSpacing: s.letterSpacing, color: s.color, transform: s.textTransform };
  };
  const btn = document.querySelector("button, a[class*=btn], a[class*=button], .btn, .button");
  const btnStyle = btn ? (() => { const s = getComputedStyle(btn); return {
      radius: s.borderRadius, padding: s.padding, bg: s.backgroundColor, color: s.color,
      border: s.border, shadow: s.boxShadow, transition: s.transition, text: btn.innerText.slice(0, 40) }; })() : null;

  // Stylesheets: keyframes, hover rules, scroll-driven animations, media queries
  const keyframes = [], hoverRules = [], features = new Set();
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }  // cross-origin sheet
    const walk = (list) => {
      for (const r of list) {
        if (r.type === CSSRule.KEYFRAMES_RULE) keyframes.push(r.cssText.slice(0, 400));
        else if (r.cssRules) walk(r.cssRules);
        else if (r.selectorText && r.selectorText.includes(":hover") && hoverRules.length < 25)
          hoverRules.push(r.cssText.slice(0, 300));
        const t = r.cssText || "";
        if (t.includes("animation-timeline")) features.add("CSS scroll-driven animations");
        if (t.includes("view-transition")) features.add("View Transitions API");
        if (t.includes("backdrop-filter")) features.add("backdrop-filter (glass effect)");
        if (t.includes("clip-path")) features.add("clip-path");
        if (t.includes("mix-blend-mode")) features.add("mix-blend-mode");
        if (t.includes("position: sticky")) features.add("sticky positioning");
        if (t.includes("scroll-snap")) features.add("scroll-snap");
        if (t.includes("@container")) features.add("container queries");
      }
    };
    walk(rules);
  }

  const scripts = [...document.scripts].map((s) => s.src).filter(Boolean);
  const libPatterns = {
    "GSAP": /gsap|greensock|TweenMax/i, "ScrollTrigger": /ScrollTrigger/i, "Lenis (smooth scroll)": /lenis/i,
    "Locomotive Scroll": /locomotive/i, "Three.js": /three(\.min)?\.js|three@|\/three\//i,
    "Lottie": /lottie|bodymovin/i, "Framer Motion": /framer-motion|framer\.com/i, "Swiper": /swiper/i,
    "Splide": /splide/i, "Barba.js": /barba/i, "AOS": /aos(\.min)?\.js|\/aos@/i, "anime.js": /anime(\.min)?\.js|animejs/i,
    "Motion One": /motion(\.min)?\.js|\/motion@/i, "Rive": /rive/i, "Spline": /spline/i, "Webflow": /webflow/i,
    "Swup": /swup/i, "Splitting.js / SplitType": /splitting|split-type/i, "Matter.js": /matter(\.min)?\.js/i,
  };
  const html = document.documentElement.outerHTML.slice(0, 400000);
  const libraries = Object.entries(libPatterns)
    .filter(([, re]) => scripts.some((s) => re.test(s)) || re.test(html.slice(0, 60000)))
    .map(([name]) => name);
  if (window.gsap) libraries.push("GSAP (global)");
  if (window.THREE) libraries.push("Three.js (global)");
  if (window.lottie) libraries.push("Lottie (global)");
  if (window.Lenis || document.documentElement.classList.contains("lenis")) libraries.push("Lenis (active)");
  if (document.querySelector("[data-aos]")) libraries.push("AOS (data-aos attributes)");
  if (document.querySelector("[data-scroll]")) features.add("data-scroll attributes");
  if (document.querySelector("[data-framer-name], [data-framer-component-type]")) libraries.push("Framer site");
  if (document.querySelector("html[data-wf-site]")) libraries.push("Webflow site");

  const animated = styles.filter(([, s]) => s.animationName && s.animationName !== "none")
    .map(([e, s]) => `${e.tagName.toLowerCase()}.${[...e.classList].slice(0, 2).join(".")} -> ${s.animationName} ${s.animationDuration} ${s.animationTimingFunction}`);
  const transitions = count(styles.map(([, s]) => s.transition)
    .filter((t) => t && !/^all 0s ease 0s$/.test(t) && !/^none/.test(t))).slice(0, 12);

  const links = uniq([...document.querySelectorAll("a[href]")]
    .map((a) => {
      try {
        const u = new URL(a.getAttribute("href"), location.href);
        if (!/^https?:$/.test(u.protocol)) return null;
        u.hash = "";
        return JSON.stringify([u.href, (a.innerText || a.getAttribute("aria-label") || "").trim().slice(0, 80)]);
      } catch (e) { return null; }
    }).filter(Boolean)).slice(0, 250).map((x) => JSON.parse(x));

  return {
    title: document.title,
    description: (document.querySelector('meta[name="description"]') || {}).content || "",
    headings: [...document.querySelectorAll("h1, h2, h3")].slice(0, 60)
      .map((h) => `${h.tagName}: ${h.innerText.trim().slice(0, 120)}`).filter((h) => h.length > 4),
    text: document.body ? document.body.innerText : "",
    links,
    typography: { h1: pick("h1"), h2: pick("h2"), body: pick("p"), nav: pick("nav a") },
    fonts, colors, button: btnStyle,
    loaded_fonts: uniq([...document.fonts].filter((f) => f.status === "loaded").map((f) => `${f.family} ${f.weight}`)).slice(0, 20),
    libraries: uniq(libraries), css_features: [...features],
    keyframes: keyframes.slice(0, 15), animated_elements: uniq(animated).slice(0, 20),
    transitions, hover_rules: hoverRules,
    counts: {
      sections: document.querySelectorAll("section").length,
      images: document.images.length, videos: document.querySelectorAll("video").length,
      canvases: document.querySelectorAll("canvas").length, svgs: document.querySelectorAll("svg").length,
      iframes: document.querySelectorAll("iframe").length,
    },
    custom_cursor: styles.some(([, s]) => s.cursor === "none") || !!document.querySelector("[class*=cursor]"),
    page_height: document.documentElement.scrollHeight,
  };
}
"""


@dataclass
class PageCapture:
    url: str
    final_url: str = ""
    ok: bool = True
    error: str = ""
    data: dict = field(default_factory=dict)
    screenshots: list[bytes] = field(default_factory=list)  # JPEG bytes

    def screenshots_b64(self) -> list[str]:
        return [base64.standard_b64encode(s).decode() for s in self.screenshots]


class Crawler:
    """Context manager that keeps one browser open for many pages."""

    def __enter__(self) -> "Crawler":
        self._pw = sync_playwright().start()
        exe = os.environ.get("CHROMIUM_PATH")  # optional: use an existing Chromium binary
        self.browser: Browser = self._pw.chromium.launch(executable_path=exe or None)
        self.context = self.browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        return self

    def __exit__(self, *exc) -> None:
        self.context.close()
        self.browser.close()
        self._pw.stop()

    def capture(self, url: str, timeout_ms: int = 45000) -> PageCapture:
        page = self.context.new_page()
        result = PageCapture(url=url)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass  # many sites never go idle; carry on
            self._scroll_through(page)
            result.final_url = page.url
            result.data = page.evaluate(EXTRACT_JS)
            result.data["text"] = result.data.get("text", "")[:MAX_TEXT_CHARS]
            result.screenshots = self._screenshots(page, result.data.get("page_height", VIEWPORT["height"]))
        except Exception as exc:  # report the failure to the agent instead of crashing
            result.ok = False
            result.error = f"{type(exc).__name__}: {exc}"[:500]
        finally:
            page.close()
        return result

    @staticmethod
    def _scroll_through(page) -> None:
        """Scroll to the bottom in steps so lazy content and scroll animations run."""
        page.evaluate(
            """async () => {
                const delay = (ms) => new Promise((r) => setTimeout(r, ms));
                let y = 0;
                for (let i = 0; i < 60 && y < document.documentElement.scrollHeight; i++) {
                    y += Math.round(window.innerHeight * 0.8);
                    window.scrollTo(0, y);
                    await delay(250);
                }
                window.scrollTo(0, 0);
                await delay(600);
            }"""
        )

    @staticmethod
    def _screenshots(page, height: int, vh: int = VIEWPORT["height"]) -> list[bytes]:
        """Screenshots at evenly spaced scroll positions (top, ..., bottom)."""
        max_y = max(0, height - vh)
        n = 1 if max_y == 0 else min(MAX_SCREENSHOTS, 1 + max_y // vh)
        shots = []
        for i in range(n):
            y = 0 if n == 1 else round(max_y * i / (n - 1))
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(700)  # let scroll-triggered animations settle
            shots.append(page.screenshot(type="jpeg", quality=70))
        return shots

    def render_local(self, path: str, width: int, height: int) -> tuple[list[bytes], list[str]]:
        """Render a local HTML file (our own design) and return screenshots + JS errors."""
        page = self.browser.new_page(viewport={"width": width, "height": height})
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(f"Uncaught error: {exc}"))
        page.on("console", lambda msg: errors.append(f"console.error: {msg.text}") if msg.type == "error" else None)
        try:
            page.goto(f"file://{os.path.abspath(path)}", wait_until="load", timeout=45000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            self._scroll_through(page)
            height_px = page.evaluate("document.documentElement.scrollHeight")
            overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
            if overflow:
                errors.append(f"Layout: horizontal overflow at {width}px wide (page is wider than the viewport).")
            return self._screenshots(page, height_px, height), errors[:20]
        finally:
            page.close()
