"""Web Design Agent: study reference websites, then design a new website for a client.

Pipeline
  1. Research - open every link you give it in a real browser, scroll through the whole
     page, take screenshots, and extract design data (colors, fonts, animation libraries,
     keyframes, hover effects ...). Claude analyses each page and picks which of its links
     are worth reading next, so the agent follows links on to other sites (up to --depth).
  2. Design  - Claude turns all the research plus your client brief into a design document
     and a complete, animated, responsive website (index.html).
  3. Review  - the new site is rendered on desktop and mobile; Claude looks at the
     screenshots and JS errors and fixes problems (--review-rounds times).

Usage
  python design_agent.py --brief "Landing page for a specialty coffee shop in Chiang Mai" \
      https://example.com/inspiration-1 https://example.com/article-about-animation
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import anthropic
from pydantic import BaseModel, Field

from crawler import Crawler, PageCapture

# ---------------------------------------------------------------------------
# Settings (override with environment variables)
# ---------------------------------------------------------------------------
ANALYST_MODEL = os.environ.get("ANALYST_MODEL", "claude-opus-5-5")
DESIGNER_MODEL = os.environ.get("DESIGNER_MODEL", "claude-opus-5-5")
ANALYST_EFFORT = os.environ.get("ANALYST_EFFORT", "medium")
DESIGNER_EFFORT = os.environ.get("DESIGNER_EFFORT", "high")
PARALLEL_ANALYSTS = int(os.environ.get("PARALLEL_ANALYSTS", "4"))

FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Server-side refusal fallback is supported on these model families.
FALLBACK_MODELS = ("claude-opus", "claude-fable", "claude-sonnet-5-5")

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
_print_lock = threading.Lock()


def log(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def fallback_kwargs(model: str) -> dict:
    if model.startswith(FALLBACK_MODELS):
        return {"betas": [FALLBACK_BETA], "fallbacks": "default"}
    return {}


def image_blocks(images_b64: list[str]) -> list[dict]:
    return [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}
        for data in images_b64
    ]


def normalize(url: str) -> str:
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


# ---------------------------------------------------------------------------
# 1. Research
# ---------------------------------------------------------------------------
class Animation(BaseModel):
    name: str = Field(description="Short name, e.g. 'staggered headline reveal'")
    where: str = Field(description="Where on the page it happens")
    trigger: str = Field(description="page load, scroll, hover, click, cursor move ...")
    description: str = Field(description="What it looks like: motion, duration, easing, feel")
    how_to_build: str = Field(description="How to implement it (CSS, GSAP, IntersectionObserver ...), concretely")


class PageAnalysis(BaseModel):
    page_type: Literal["website_showcase", "article_or_tutorial", "gallery_or_collection", "documentation", "other"]
    relevance: Literal["high", "medium", "low"] = Field(description="Relevance to the client brief")
    summary: str
    visual_style: str = Field(description="Overall look and mood, grid, spacing, imagery, visual hierarchy")
    color_palette: list[str] = Field(description="Hex colors with their role, e.g. '#0F0F0F - background'")
    typography: str = Field(description="Fonts, sizes, weights, scale, and how type is used")
    layout_patterns: list[str] = Field(description="Section patterns worth reusing (hero, bento grid, marquee ...)")
    animations: list[Animation]
    interactions: list[str] = Field(description="Hover effects, cursor, menus, carousels, transitions, micro-interactions")
    ux_and_conversion: list[str] = Field(description="CTAs, trust signals, information architecture, copy ideas")
    knowledge: list[str] = Field(description="Lessons, techniques, rules or tips taught by the page (esp. articles)")
    tools_and_libraries: list[str]
    ideas_for_client: list[str] = Field(description="Concrete ideas to apply to the client's new website")
    links_to_follow: list[str] = Field(description="URLs copied exactly from the page's link list worth reading next")


ANALYST_SYSTEM = """You are a senior web designer and front-end developer studying reference material for a client project.
You receive screenshots of a page (top to bottom), measured design data extracted from the live page, its full text,
and its links. Study ALL of it carefully and report what a designer could learn and reuse.

- Base colors and fonts on the measured data and screenshots, not guesses. Describe motion concretely
  (what moves, direction, duration, easing, stagger, trigger) and explain how to build it.
- If the page is an article, tutorial, or collection, extract its knowledge and techniques in detail.
- For links_to_follow, choose only links likely to teach something useful for the client brief: examples, case
  studies, tutorials, demos, showcased sites, or deeper articles. Skip login, legal, social share, ads, and
  pure navigation. Copy URLs exactly from the provided list. Return an empty list if nothing qualifies.
- Write in the same language as the client brief."""


def analyze_page(capture: PageCapture, brief: str, max_links: int) -> PageAnalysis | None:
    data = dict(capture.data)
    text = data.pop("text", "")
    links = data.pop("links", [])
    link_lines = "\n".join(f"- {url}  ({label})" if label else f"- {url}" for url, label in links)

    content = image_blocks(capture.screenshots_b64())
    content.append({
        "type": "text",
        "text": (
            f"Client brief:\n{brief}\n\n"
            f"Page URL: {capture.final_url or capture.url}\n\n"
            f"Measured design data (JSON):\n{json.dumps(data, ensure_ascii=False, indent=1)}\n\n"
            f"Full page text:\n{text}\n\n"
            f"Links on the page (choose at most {max_links} to follow):\n{link_lines or '(none)'}"
        ),
    })

    response = client.beta.messages.parse(
        model=ANALYST_MODEL,
        max_tokens=16000,
        system=ANALYST_SYSTEM,
        output_config={"effort": ANALYST_EFFORT},
        output_format=PageAnalysis,
        messages=[{"role": "user", "content": content}],
        **fallback_kwargs(ANALYST_MODEL),
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return None

    analysis = response.parsed_output
    allowed = {normalize(url) for url, _ in links}
    analysis.links_to_follow = [u for u in analysis.links_to_follow if normalize(u) in allowed][:max_links]
    return analysis


def research(seeds: list[str], brief: str, depth: int, max_pages: int, max_links: int, out: Path) -> list[dict]:
    shots_dir = out / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    visited: set[str] = set()
    results: list[dict] = []
    level = [(u, None) for u in seeds]  # (url, found_on)

    with Crawler() as crawler, ThreadPoolExecutor(max_workers=PARALLEL_ANALYSTS) as pool:
        for current_depth in range(depth + 1):
            todo = []
            for url, parent in level:
                key = normalize(url)
                if key in visited or len(visited) >= max_pages:
                    continue
                visited.add(key)
                todo.append((url, parent))
            if not todo:
                break

            futures = []
            for url, parent in todo:
                n = len(results) + len(futures) + 1
                log(f"[read {n}] depth {current_depth}: {url}")
                capture = crawler.capture(url)
                if not capture.ok:
                    log(f"[read {n}] failed: {capture.error}")
                    results.append({"url": url, "found_on": parent, "depth": current_depth, "error": capture.error})
                    continue
                for i, shot in enumerate(capture.screenshots):
                    (shots_dir / f"page{n:02d}-{i + 1}.jpg").write_bytes(shot)
                futures.append((n, url, parent, capture, pool.submit(analyze_page, capture, brief, max_links)))

            next_level = []
            for n, url, parent, capture, future in futures:
                try:
                    analysis = future.result()
                except anthropic.APIError as exc:
                    log(f"[analyse {n}] API error: {exc}")
                    results.append({"url": url, "found_on": parent, "depth": current_depth, "error": str(exc)})
                    continue
                if analysis is None:
                    log(f"[analyse {n}] the model declined to analyse this page")
                    continue
                log(f"[analyse {n}] {analysis.relevance} relevance, {len(analysis.animations)} animations, "
                    f"{len(analysis.links_to_follow)} links to follow")
                results.append({
                    "id": n, "url": capture.final_url or url, "found_on": parent, "depth": current_depth,
                    "title": capture.data.get("title", ""),
                    "measured": {k: capture.data.get(k) for k in
                                 ("fonts", "loaded_fonts", "colors", "libraries", "css_features", "typography")},
                    "analysis": analysis.model_dump(),
                })
                next_level += [(link, url) for link in analysis.links_to_follow]
            level = next_level

    results.sort(key=lambda r: r.get("id", 999))
    return results


def research_markdown(results: list[dict]) -> str:
    lines = ["# Research notes\n"]
    for r in results:
        if "error" in r:
            lines.append(f"## ⚠️ {r['url']}\nCould not read: {r['error']}\n")
            continue
        a = r["analysis"]
        lines += [
            f"## {r['id']}. {r['title'] or r['url']}",
            f"<{r['url']}>  · {a['page_type']} · relevance: **{a['relevance']}**"
            + (f" · found on {r['found_on']}" if r["found_on"] else ""),
            "", a["summary"], "",
            f"**Visual style:** {a['visual_style']}", "",
            f"**Typography:** {a['typography']}", "",
            "**Colors:** " + ", ".join(a["color_palette"]), "",
        ]
        if a["animations"]:
            lines.append("**Animations**")
            lines += [f"- *{x['name']}* ({x['trigger']}, {x['where']}): {x['description']}  \n"
                      f"  ↳ How: {x['how_to_build']}" for x in a["animations"]]
            lines.append("")
        for title, key in [("Layout patterns", "layout_patterns"), ("Interactions", "interactions"),
                           ("UX & conversion", "ux_and_conversion"), ("Knowledge", "knowledge"),
                           ("Tools & libraries", "tools_and_libraries"), ("Ideas for the client", "ideas_for_client")]:
            if a[key]:
                lines.append(f"**{title}**")
                lines += [f"- {x}" for x in a[key]]
                lines.append("")
        lines.append(f"Screenshots: `screenshots/page{r['id']:02d}-*.jpg`\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. Design
# ---------------------------------------------------------------------------
DESIGNER_SYSTEM = """You are an award-level web designer and creative front-end developer.
You design websites that win clients: a clear concept, strong visual identity, purposeful motion, and copy that sells.

You are given a client brief and research notes about reference websites and articles. Use the research as
inspiration and technique — combine and adapt the best ideas into something original for this client.
Never copy text, logos, images, or brand assets from the references.

Respond with exactly two parts:

<design_doc>
A Markdown design document for presenting to the client: concept and mood; color palette (hex + role);
typography (Google Fonts) and type scale; sitemap and section-by-section layout; motion spec (for each animation:
element, trigger, duration, easing, and which reference inspired it, by URL); interactions and micro-interactions;
responsive behaviour; accessibility notes; and a list of the references used.
</design_doc>

<html>
The complete website as ONE self-contained index.html:
- Semantic HTML, inline <style> and <script>. Mobile-first and responsive (360px to 1920px), no horizontal overflow.
- Fonts from Google Fonts. Animations with CSS and vanilla JS; if you need GSAP, load it only from
  https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js (and ScrollTrigger.min.js from the same folder).
- No external images: use CSS gradients, inline SVG, or clearly labelled placeholder blocks the client will
  replace with real photos.
- Real, persuasive copy for the client's business in the client brief's language, with clear calls to action.
- Respect prefers-reduced-motion, keep good color contrast, visible focus states, and working keyboard navigation.
- No JavaScript errors. Content must be visible even if a script fails.
</html>"""

REVIEW_SYSTEM = """You are a meticulous design director reviewing a website before it is shown to a client.
You get the brief, the design document, the current index.html, screenshots on desktop (1440px) and mobile (390px),
and any JavaScript errors or layout problems detected in the browser.

Find what hurts the result: bugs, JS errors, broken or overlapping layout, horizontal overflow, invisible
content (e.g. elements stuck at opacity 0), weak hierarchy, poor contrast, awkward spacing, motion that does not
match the design doc, mobile issues, weak copy or CTAs. Then fix them.

Respond with exactly two parts:
<changes>A short bullet list of what you changed and why.</changes>
<html>The complete, corrected index.html (the whole file, not a diff).</html>"""


def stream_text(model: str, system: str, content: list[dict], effort: str) -> str:
    with client.beta.messages.stream(
        model=model,
        max_tokens=64000,
        system=system,
        output_config={"effort": effort},
        messages=[{"role": "user", "content": content}],
        **fallback_kwargs(model),
    ) as stream:
        response = stream.get_final_message()
    if response.stop_reason == "refusal":
        raise RuntimeError("The model declined this request.")
    if response.stop_reason == "max_tokens":
        log("[warn] the response hit max_tokens and may be cut off")
    return "\n".join(b.text for b in response.content if b.type == "text")


def extract(tag: str, text: str) -> str:
    match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", text, re.S)
    if not match:
        raise ValueError(f"The model's answer did not contain <{tag}>...</{tag}>.")
    body = match.group(1)
    return re.sub(r"^```(?:html|markdown|md)?\s*|\s*```$", "", body.strip())


def design(brief: str, results: list[dict], out: Path) -> tuple[str, str]:
    usable = [r for r in results if "analysis" in r and r["analysis"]["relevance"] != "low"] or \
             [r for r in results if "analysis" in r]
    log(f"[design] designing from {len(usable)} researched page(s)...")
    notes = json.dumps(
        [{"url": r["url"], "measured": r["measured"], **r["analysis"]} for r in usable],
        ensure_ascii=False, indent=1,
    )
    # Show the designer the first screenshot of the most relevant pages as visual references.
    shots_dir = out / "screenshots"
    top = sorted(usable, key=lambda r: {"high": 0, "medium": 1, "low": 2}[r["analysis"]["relevance"]])[:6]
    content = []
    for r in top:
        shot = shots_dir / f"page{r['id']:02d}-1.jpg"
        if shot.exists():
            content.append({"type": "text", "text": f"Reference screenshot: {r['url']}"})
            content += image_blocks([base64.standard_b64encode(shot.read_bytes()).decode()])
    content.append({"type": "text", "text": f"Client brief:\n{brief}\n\nResearch notes (JSON):\n{notes}"})

    answer = stream_text(DESIGNER_MODEL, DESIGNER_SYSTEM, content, DESIGNER_EFFORT)
    return extract("design_doc", answer), extract("html", answer)


def review(brief: str, design_doc: str, html_path: Path, rounds: int) -> None:
    for i in range(1, rounds + 1):
        log(f"[review {i}] rendering the site on desktop and mobile...")
        with Crawler() as crawler:
            desktop, errors_d = crawler.render_local(str(html_path), 1440, 900)
            mobile, errors_m = crawler.render_local(str(html_path), 390, 844)
        problems = sorted(set(errors_d + errors_m))
        log(f"[review {i}] {len(problems)} browser problem(s) found; asking for fixes...")

        content = [{"type": "text", "text": "Desktop screenshots (1440px, top to bottom):"}]
        content += image_blocks([base64.standard_b64encode(s).decode() for s in desktop])
        content.append({"type": "text", "text": "Mobile screenshots (390px, top to bottom):"})
        content += image_blocks([base64.standard_b64encode(s).decode() for s in mobile])
        content.append({"type": "text", "text": (
            f"Client brief:\n{brief}\n\nDesign document:\n{design_doc}\n\n"
            f"Browser problems detected:\n" + ("\n".join(problems) or "(none)") +
            f"\n\nCurrent index.html:\n{html_path.read_text(encoding='utf-8')}"
        )})

        answer = stream_text(DESIGNER_MODEL, REVIEW_SYSTEM, content, DESIGNER_EFFORT)
        html_path.with_name(f"index.v{i}.html").write_text(html_path.read_text(encoding="utf-8"), encoding="utf-8")
        html_path.write_text(extract("html", answer), encoding="utf-8")
        try:
            log(f"[review {i}] changes:\n{extract('changes', answer)}")
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description="Research reference websites and design a new website for a client.")
    p.add_argument("urls", nargs="*", help="Reference links to read (websites, articles, galleries ...)")
    p.add_argument("--urls-file", help="Text file with one link per line")
    p.add_argument("--brief", help="Client brief: business, audience, goals, mood, sections, language ...")
    p.add_argument("--brief-file", help="Read the client brief from a text file")
    p.add_argument("--depth", type=int, default=1, help="How many hops of links to follow (0 = only your links)")
    p.add_argument("--max-pages", type=int, default=12, help="Maximum number of pages to read in total")
    p.add_argument("--max-links-per-page", type=int, default=4, help="Links to follow from each page")
    p.add_argument("--review-rounds", type=int, default=1, help="Rounds of render-and-fix for the new site")
    p.add_argument("--research", help="Reuse research.json from an earlier run (skips reading links)")
    p.add_argument("--out", help="Output folder (default: projects/<time>-<brief>)")
    args = p.parse_args()

    brief = Path(args.brief_file).read_text(encoding="utf-8") if args.brief_file else (args.brief or "")
    if not brief.strip():
        sys.exit("Please describe the client project with --brief or --brief-file.")
    urls = list(args.urls)
    if args.urls_file:
        urls += [l.strip() for l in Path(args.urls_file).read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.startswith("#")]
    if not urls and not args.research:
        sys.exit("Please give at least one reference link (or --research to reuse earlier research).")

    slug = re.sub(r"[^\w฀-๿]+", "-", brief.lower()).strip("-")[:40] or "project"
    out = Path(args.out or f"projects/{datetime.now():%Y%m%d-%H%M%S}-{slug}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "brief.txt").write_text(brief, encoding="utf-8")

    if args.research:
        src = Path(args.research)
        results = json.loads(src.read_text(encoding="utf-8"))
        if src.parent.resolve() != out.resolve() and (src.parent / "screenshots").exists():
            shutil.copytree(src.parent / "screenshots", out / "screenshots", dirs_exist_ok=True)
    else:
        results = research(urls, brief, args.depth, args.max_pages, args.max_links_per_page, out)
        (out / "research.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        (out / "research.md").write_text(research_markdown(results), encoding="utf-8")
        log(f"[research] read {len(results)} page(s) -> {out / 'research.md'}")

    if not any("analysis" in r for r in results):
        sys.exit("No page could be read and analysed, so there is nothing to design from.")

    design_doc, html = design(brief, results, out)
    (out / "design.md").write_text(design_doc, encoding="utf-8")
    html_path = out / "index.html"
    html_path.write_text(html, encoding="utf-8")
    log(f"[design] wrote {out / 'design.md'} and {html_path}")

    if args.review_rounds > 0:
        review(brief, design_doc, html_path, args.review_rounds)

    print(f"\nDone. Open {html_path.resolve()} in your browser.")
    print(f"Design document: {out / 'design.md'}   Research: {out / 'research.md'}")


if __name__ == "__main__":
    main()
