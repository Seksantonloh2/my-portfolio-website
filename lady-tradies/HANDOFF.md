# Lady Tradies Australia — 3D concept rebuild (Framer handoff)

Open `index.html` in a browser. It's a single self-contained file with no libraries; Switzer and Inter fonts load from the web.

## Sections
1. Header: logo, nav, "Find a tradie" CTA (fixed; turns light over light sections)
2. Hero (dark), split layout: H1 + trade/postcode finder on the left, live 3D wireframe house on the right that builds itself on a loop and can be dragged to turn
3. Trust bar: 4 count-up stats (**placeholder figures**)
4. **Signature moment: "Every trade. Her hands."**, a 620vh pinned scroll story. The 3D house is built in 5 stages (Carpenter → Electrician → Plumber → Painter/Tiler → Landscaper). It has a HUD counter, stage copy that blur-swaps, a tape-measure progress bar, a "▶ Watch it go up" autoplay button and a skip link
5. Trades: numbered divider rows with an image preview that follows the cursor. Clicking a row fills in the hero finder
6. How it works: 3 numbered steps
7. Getting started: a 3-question "which trade suits you?" quiz (decision tool)
8. For tradeswomen: split image/text with perks and a "List my business" CTA
9. Stories: bento review cards (**placeholder reviews**)
10. Coverage: 8 states/territories with green "listings open" status dots
11. FAQ accordion
12. Final CTA, footer (ABN/email/phone placeholders), sticky offer bar (hidden during the story)

## Tokens
- Colours: ink `#0A0A0A`, paper `#FAFAF8`, paper-2 `#F1F0EC`, line `#E4E2DC` / `#262626`, muted `#6B6A66` / `#8E8D88`
- Accent (single): hi-vis amber `#FFC21A`. Status: ok `#16A34A`, error `#DC2626`
- Type: Switzer 600 for display (tracking -3.5%, line-height 0.95), Inter for body, JetBrains Mono uppercase for eyebrows and HUD labels
- Scale: hero title 112 / subtitle 22 (desktop), 56 / 16 (mobile). H2 88 / 22
- Radius: 14 for cards, 24 for large panels, pill for buttons. Spacing: 4/8/16/24/32/48/64/96/128. Section padding 96–160

## Motion → Framer
- Text: Appear effect with blur 10 → 0, opacity 0 → 1, y 16 → 0, 0.7s, cubic-bezier(.22,1,.36,1), 70ms stagger per word
- Sections: scroll-triggered Appear with blur 8, y 24, 0.8s
- Buttons: hover variant where the label slides up and a duplicate replaces it, and the arrow rotates -45°. Press scale 0.97
- Rows/cards: hover lift of 4px, border colour change, image scale 1.05. **No shadows**
- Numbers: count-up code component (1.5s ease-out, runs once)
- Nav: smooth scroll only. Use a blurred page transition between separate pages only
- Code components needed: `House3D` (the canvas renderer, with `progress` and `interactive` props), scroll-progress wrapper for the story, quiz, finder

## Still needed from the client
Logo, real photos (every `.ph` block is a labelled placeholder), verified stats, reviews, ABN, contact details, licence-verification policy, listing fee/process, and the real directory search URL (`finder` submit handler in the script).
