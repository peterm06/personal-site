#!/usr/bin/env python3
"""Generate reading/index.html from the StoryGraph export in data/reading/.

A book mosaic: one small square per book, in the order they were finished,
grouped into a block per year (newest on top). Each year's books wrap at a fixed
number per row so no row runs the full page width. Color is categorical, not a
scale -- five-star books are filled from a metallic gradient, everything else is
one flat slate.

The metal is a single <linearGradient> in userSpaceOnUse coordinates spanning the
whole grid, so each five-star square samples a different part of the ramp
according to where it sits. That positional variation is what reads as metal; a
gradient inside one 10px square would be invisible. It also drifts slowly, which
echoes the sheen animation on the site's <h1>.

Squares carry a <title> child, which gives a native browser tooltip (book,
author, month) on hover with no JavaScript. Only the wide layout gets them --
the narrow layout is for touch screens, where there is no hover.

The page is pre-rendered (both SVGs are baked into the HTML) so it works with no
JavaScript and no build step. Re-run after updating the export:

    python3 scripts/gen_reading.py

It reads:  data/reading/storygraph_export.csv
and writes: reading/index.html  (served at /reading)

The directory-plus-index layout matches workouts/ -- it yields the clean
/reading URL on any static host without extensionless-URL rewriting.
"""

import csv
import datetime as dt
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "reading", "storygraph_export.csv")
OUT = os.path.join(ROOT, "reading", "index.html")

# --- geometry (SVG user units; each SVG scales to its container via viewBox) ---
CELL = 10
GAP = 3
PITCH = CELL + GAP
YEAR_LABEL_H = 19   # space above each year's rows for its heading
YEAR_GAP = 20       # space between year blocks
PER_ROW_WIDE = 40   # books per row on desktop
PER_ROW_NARROW = 24 # books per row under the mobile breakpoint

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def read_books():
    """Every finished book as (date, title, author, is_five), oldest first."""
    books = []
    with open(SRC) as f:
        for r in csv.DictReader(f):
            raw = r["Last Date Read"].strip()
            if not raw:
                continue
            d = dt.date(*(int(p) for p in raw.split("/")))
            author = r["Authors"].strip()
            if len(author) > 60:  # a few rows list a dozen contributors
                author = author[:57].rstrip(", ") + "…"
            books.append((d, r["Title"].strip(), author,
                          r["Star Rating"].strip() == "5.0"))
    books.sort(key=lambda b: b[0])
    return books


def fmt_long(d):
    """'August 8, 2026' -- strftime('%-d') is not portable, so build it here."""
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def by_year(books):
    years = {}
    for b in books:
        years.setdefault(b[0].year, []).append(b)
    return years


def build_svg(years, per_row, wide):
    """One block per year, newest on top; books wrap at per_row.

    Only the wide layout carries data-b labels. The narrow layout deliberately
    omits them -- both layouts emit the same books in the same order, so the
    click handler looks a square up in the wide layout by index instead.
    Duplicating 1,383 labels would nearly double the gzipped page for no gain.

    These are data-b attributes rather than <title> children on purpose: a
    <title> forces a native hover tooltip, which would compete with the readout
    bar the click handler drives.
    """
    order = sorted(years, reverse=True)
    width = per_row * PITCH - GAP

    parts = []
    y = 2
    for year in order:
        books = years[year]
        rows = -(-len(books) // per_row)  # ceil
        parts.append(
            f'<text class="yr" x="0" y="{y + 13}">{year}</text>'
            f'<text class="yn" x="{width}" y="{y + 13}" text-anchor="end">'
            f'{len(books)} book{"s" if len(books) != 1 else ""}</text>'
        )
        grid_top = y + YEAR_LABEL_H
        for i, (d, title, author, is_five) in enumerate(books):
            cx = (i % per_row) * PITCH
            cy = grid_top + (i // per_row) * PITCH
            cls = "b five" if is_five else "b"
            rect = (f'<rect class="{cls}" x="{cx}" y="{cy}" '
                    f'width="{CELL}" height="{CELL}" rx="2"')
            if wide:
                star = "★ " if is_five else ""
                who = f" — {author}" if author else ""
                when = f" · {MONTHS[d.month - 1]} {d.year}"
                label = esc(f"{star}{title}{who}{when}")
                parts.append(f'{rect} data-b="{label}"/>')
            else:
                parts.append(f"{rect}/>")
        y = grid_top + rows * PITCH + YEAR_GAP

    height = y - YEAR_GAP + 2
    hint = " Select any square for the book, author, and month."
    return (
        f'<svg class="mosaic {"wide" if wide else "narrow"}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'preserveAspectRatio="xMinYMin meet" '
        f'aria-label="One square per book, grouped by year from '
        f'{order[0]} at the top down to {order[-1]}. Five-star books are '
        f'picked out in metallic gold.{hint}">'
        + "".join(parts) + "</svg>"
    )


def build_list(years):
    """Five-star books only, grouped by year (newest first), in finish order."""
    blocks = []
    for year in sorted(years, reverse=True):
        books = years[year]
        fives = [b for b in books if b[3]]
        if not fives:
            continue
        items = "".join(
            f'<li><span class="bullet" aria-hidden="true"></span>'
            f'<span class="txt"><span class="t">{esc(title)}</span>'
            # a couple of rows have no author; skip the span so no blank line
            + (f'<span class="a">{esc(author)}</span>' if author else "")
            + f'</span><span class="m">{MONTHS[d.month - 1]}</span></li>'
            for d, title, author, _ in fives
        )
        blocks.append(
            f'<div class="ygroup"><h2>{year}'
            f'<span class="yn">{len(fives)} of {len(books)} books</span></h2>'
            f"<ul>{items}</ul></div>"
        )
    return "\n        ".join(blocks)


HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Reading — Peter Miller</title>
    <meta
      name="description"
      content="Every book finished since 2008, one square at a time."
    />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="icon" href="/favicon.ico" sizes="32x32" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Atkinson+Hyperlegible:wght@400;700&display=swap"
      rel="stylesheet"
    />
    <style>
      :root {{
        --ink: #0f1218;
        --paper: #e9ebee;
        --muted: #8f98a3;
        --hairline: #232a34;
        --jade: #4cc8a3;
        --sky: #5aa8e8;
        --indigo: #7b83ea;
        --violet: #a982e3;
        --sheen-edge: var(--paper);

        /* book mosaic: one flat slate for every book, a metal ramp for 5 stars.
           The ramp is bright at its peak -- on the dark ink those highlights
           read as light catching a surface. Its floor stays high on purpose:
           the variation is decorative, so no square should look dim enough to
           suggest it is somehow *less* of a five-star than its neighbour. */
        --book: #3f4d60;
        --metal-1: #a8822f;
        --metal-2: #dcb468;
        --metal-3: #f6e4b2;
        --metal-4: #cfa147;
        --metal-5: #b28f3c;
        --metal-flat: #d4a24c;
      }}

      [data-theme='light'] {{
        --ink: #f2f3f5;
        --paper: #1a2028;
        --muted: #5c6672;
        --hairline: #d6dae0;
        --jade: #1f9a78;
        --sky: #2f7fc4;
        --indigo: #5560cf;
        --violet: #7e58c4;
        --sheen-edge: #1a2028;

        /* Light mode inverts the problem. A metal's bright specular highlight
           is invisible on paper, so here the ramp lives in a narrow mid-dark
           band and gets its metallic quality from saturation shifts instead.
           The neutral is lightened so five stars separate by value as well as
           hue -- hue alone would fail for colourblind readers. */
        --book: #c0c9d3;
        --metal-1: #7a5a12;
        --metal-2: #a8801f;
        --metal-3: #c9a134;
        --metal-4: #96701a;
        --metal-5: #86641a;
        --metal-flat: #96701a;
      }}

      * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }}

      html {{
        height: 100%;
        /* reserve the scrollbar gutter on every page: the landing page does not
           scroll and this one does, so without this the centred content and the
           fixed toggle shift sideways by the scrollbar width on navigation */
        scrollbar-gutter: stable;
      }}

      body {{
        min-height: 100%;
        display: grid;
        justify-items: center;
        align-content: start;
        background: var(--ink);
        color: var(--paper);
        font-family: 'Atkinson Hyperlegible', system-ui, sans-serif;
        font-size: 1.0625rem;
        line-height: 1.6;
        padding: clamp(3rem, 10vh, 6rem) 1.5rem 4rem;
        transition:
          background 240ms ease,
          color 240ms ease;
      }}

      main {{
        width: 100%;
        max-width: 44rem;
      }}

      /* --- Cross-document view transitions ---
         Same-origin navigations cross-fade instead of hard-cutting. Requires
         http(s) (not file://) and is Chrome/Safari-only today; unsupported
         browsers just navigate instantly, so this is purely additive. */
      @view-transition {{
        navigation: auto;
      }}

      @media (prefers-reduced-motion: reduce) {{
        @view-transition {{
          navigation: none;
        }}
      }}

      .eyebrow {{
        color: var(--muted);
        font-size: 0.875rem;
        letter-spacing: 0.02em;
      }}

      .eyebrow a {{
        color: var(--muted);
        text-decoration: none;
        border-bottom: 1px solid var(--hairline);
      }}

      .eyebrow a:hover,
      .eyebrow a:focus-visible {{
        color: var(--paper);
      }}

      h1 {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: clamp(2.2rem, 7vw, 3rem);
        letter-spacing: -0.015em;
        line-height: 1.2;
        padding-bottom: 0.12em; /* room for descenders under background-clip: text */
        margin-top: 0.4rem;
        background: linear-gradient(
          100deg,
          var(--sheen-edge) 0%,
          var(--jade) 28%,
          var(--sky) 44%,
          var(--indigo) 60%,
          var(--violet) 76%,
          var(--sheen-edge) 100%
        );
        background-size: 220% 100%;
        background-position: 0% 0;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        animation: sheen 14s ease-in-out infinite alternate;
      }}

      @keyframes sheen {{
        from {{ background-position: 0% 0; }}
        to {{ background-position: 100% 0; }}
      }}

      @media (prefers-reduced-motion: reduce) {{
        h1 {{ animation: none; background-position: 50% 0; }}
      }}

      .lede {{
        margin-top: 0.75rem;
        color: var(--muted);
        max-width: 42rem;
      }}

      /* --- summary card --- */
      .summary-card {{
        margin-top: 2.25rem;
        border: 1px solid var(--hairline);
        border-radius: 14px;
        padding: 1.5rem 2rem;
        width: fit-content;
        max-width: 100%;
      }}
      .summary-primary {{
        display: flex;
        flex-wrap: wrap;
        gap: 2.5rem;
        align-items: baseline;
      }}
      .stat .num {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 2.2rem;
        line-height: 1;
      }}
      .stat .lbl {{
        color: var(--muted);
        font-size: 0.8rem;
        margin-top: 0.25rem;
      }}
      .summary-primary .stat:first-child .num {{
        font-size: 2.8rem;
      }}
      .num .dot {{
        display: inline-block;
        width: 16px;
        height: 16px;
        border-radius: 4px;
        margin-right: 0.5rem;
        vertical-align: 0.06em;
        background: linear-gradient(
          135deg,
          var(--metal-2),
          var(--metal-3),
          var(--metal-4),
          var(--metal-1)
        );
      }}

      /* --- the mosaic --- */
      .hero {{
        margin-top: 2.25rem;
      }}
      svg.mosaic {{
        display: block;
        width: 100%;
        height: auto;
        overflow: visible;
      }}
      svg.narrow {{ display: none; }}

      .mosaic .yr {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 13px;
        fill: var(--muted);
      }}
      .mosaic .yn {{
        font-family: 'Atkinson Hyperlegible', sans-serif;
        font-size: 9.5px;
        fill: var(--muted);
        opacity: 0.75;
      }}

      .mosaic .b {{
        fill: var(--book);
        cursor: pointer;
      }}
      .mosaic .five {{
        fill: url(#metal);
      }}

      /* Hover previews the target, .sel marks the square whose book is showing.
         --paper inverts with the theme, so the outline reads against both the
         slate and the gold. The stroke is centred on the edge, so half of it
         sits in the 3px gutter and never touches a neighbour. */
      .mosaic .b:hover,
      .mosaic .b.sel {{
        stroke: var(--paper);
        stroke-width: 1.5;
      }}

      /* Under reduced motion, skip the drifting gradient entirely and use one
         flat metal tone -- SMIL animation cannot be paused from CSS. */
      @media (prefers-reduced-motion: reduce) {{
        .mosaic .five {{ fill: var(--metal-flat); }}
      }}

      footer {{
        margin-top: 3rem;
        color: var(--muted);
        font-size: 0.8rem;
        opacity: 0.8;
      }}

      .hint {{
        margin-top: 1.1rem;
        color: var(--muted);
        font-size: 0.8rem;
        opacity: 0.8;
      }}

      /* --- readout: a bar pinned to the bottom, at every width. Selecting a
             square is the one way to read a book off the mosaic, so the same
             treatment runs on desktop and touch alike. --- */
      .readout {{
        display: none;
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 10;
        background: var(--ink);
        border-top: 1px solid var(--hairline);
        color: var(--paper);
        font-size: 0.85rem;
        line-height: 1.45;
        padding: 0.85rem 1.25rem;
        padding-bottom: calc(0.85rem + env(safe-area-inset-bottom));
      }}
      .readout.show {{
        display: flex;
        justify-content: center;
      }}
      /* keep the text lined up with the page's own column instead of the
         far-left edge of a wide bar */
      .readout span {{
        width: 100%;
        max-width: 44rem;
      }}
      /* nothing is hidden behind the fixed bar */
      body:has(.readout.show) {{ padding-bottom: 7rem; }}
      /* the readout describes a square in the mosaic, so it goes away with it */
      body:has(#five-stars:target) .readout {{ display: none; }}

      /* --- view switch: an iOS-style toggle --- */
      .switchwrap {{
        position: relative;
        display: inline-grid;
        justify-items: center;
        gap: 0.4rem;
        margin-left: auto; /* pushes it to the far edge of the card */
        align-self: center;
      }}
      .switchtrack {{
        width: 46px;
        height: 27px;
        border-radius: 999px;
        background: var(--hairline);
        position: relative;
        transition: background 220ms ease;
      }}
      .knob {{
        position: absolute;
        top: 3px;
        left: 3px;
        width: 21px;
        height: 21px;
        border-radius: 50%;
        background: var(--muted);
        transition:
          transform 220ms cubic-bezier(0.4, 0, 0.2, 1),
          background 220ms ease;
      }}
      .switchlbl {{
        font-size: 0.75rem;
        line-height: 1;
        color: var(--muted);
        white-space: nowrap;
        transition: color 200ms ease;
      }}

      /* the whole wrap is clickable, label included; only one anchor shows */
      .hit {{
        position: absolute;
        inset: -4px;
        border-radius: 10px;
      }}
      .to-mosaic {{ display: none; }}
      .hit:focus-visible {{
        outline: 2px solid var(--indigo);
        outline-offset: 2px;
      }}

      /* "on" state. The knob takes --ink, which is the page background and so
         is always the opposite of the gold it sits on, in either theme. */
      body:has(#five-stars:target) .switchtrack {{
        background: var(--metal-flat);
      }}
      body:has(#five-stars:target) .knob {{
        transform: translateX(19px);
        background: var(--ink);
      }}
      body:has(#five-stars:target) .switchlbl {{ color: var(--paper); }}
      body:has(#five-stars:target) .to-list {{ display: none; }}
      body:has(#five-stars:target) .to-mosaic {{ display: block; }}

      @media (prefers-reduced-motion: reduce) {{
        .knob,
        .switchtrack,
        .switchlbl {{ transition: none; }}
      }}

      /* --- five-star list view --- */
      .list-view {{
        display: none;
        margin-top: 2.25rem;
        /* Jumping to #five-stars would scroll the list to the top of the
           viewport, taking the switch with it and leaving no way back. An
           oversized scroll margin puts the target above the document start, so
           the browser clamps to the top and nothing moves -- while the URL stays
           shareable. */
        scroll-margin-top: 100vh;
      }}
      body:has(#five-stars:target) .hero {{ display: none; }}
      body:has(#five-stars:target) .list-view {{ display: block; }}
      .ygroup + .ygroup {{ margin-top: 2rem; }}
      .ygroup h2 {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 1.15rem;
        color: var(--muted);
        display: flex;
        align-items: baseline;
        gap: 0.6rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--hairline);
      }}
      .ygroup h2 .yn {{
        font-family: 'Atkinson Hyperlegible', sans-serif;
        font-size: 0.75rem;
        font-weight: 400;
        margin-left: auto;
        opacity: 0.75;
      }}
      .ygroup ul {{
        list-style: none;
        margin-top: 0.85rem;
        display: grid;
        gap: 0.9rem;
      }}
      .ygroup li {{
        display: grid;
        grid-template-columns: 11px 1fr auto;
        gap: 0.7rem;
        align-items: baseline;
        font-size: 0.95rem;
        line-height: 1.4;
      }}
      /* title on its own line, author beneath it */
      .ygroup .t,
      .ygroup .a {{ display: block; }}
      .ygroup .bullet {{
        width: 11px;
        height: 11px;
        border-radius: 3px;
        /* the SVG gradient cannot be reused in HTML, so this is the same ramp
           expressed as a CSS gradient -- matching the legend and card dot */
        background: linear-gradient(
          135deg,
          var(--metal-2),
          var(--metal-3),
          var(--metal-4),
          var(--metal-1)
        );
        transform: translateY(0.1em);
      }}
      .ygroup .a {{
        color: var(--muted);
        font-size: 0.85rem;
        margin-top: 0.15rem;
      }}
      .ygroup .m {{
        color: var(--muted);
        font-size: 0.75rem;
        white-space: nowrap;
        opacity: 0.7;
      }}

      /* --- narrow screens: fewer books per row so squares stay legible --- */
      @media (max-width: 600px) {{
        .summary-card {{ width: 100%; }}
        .summary-primary {{
          justify-content: center;
          text-align: center;
          gap: 1.25rem 2.5rem;
        }}
        /* the total gets its own row, the other stat shares the next one --
           without this they wrap lopsided */
        .summary-primary .stat:first-child {{ flex-basis: 100%; }}
        /* the switch drops to its own centred row rather than hugging an edge */
        .switchwrap {{
          margin-left: 0;
          justify-self: center;
        }}
        svg.wide {{ display: none; }}
        svg.narrow {{ display: block; }}
      }}

      /* --- theme toggle (same as index) --- */
      #theme-toggle {{
        position: fixed;
        top: 1.25rem;
        right: 1.25rem;
        width: 2.5rem;
        height: 2.5rem;
        view-transition-name: theme-toggle; /* stays put across navigations */
        display: grid;
        place-items: center;
        background: transparent;
        border: 1px solid var(--hairline);
        border-radius: 50%;
        color: var(--muted);
        cursor: pointer;
        transition:
          color 160ms ease,
          border-color 160ms ease;
      }}
      #theme-toggle:hover,
      #theme-toggle:focus-visible {{
        color: var(--paper);
        border-color: var(--muted);
      }}
      #theme-toggle:focus-visible {{
        outline: 2px solid var(--indigo);
        outline-offset: 3px;
      }}
      #theme-toggle svg {{ width: 1.125rem; height: 1.125rem; }}
      #theme-toggle .sun {{ display: none; }}
      #theme-toggle .moon {{ display: block; }}
      [data-theme='light'] #theme-toggle .sun {{ display: block; }}
      [data-theme='light'] #theme-toggle .moon {{ display: none; }}
    </style>
    <script>
      /* Runs before first paint so the stored theme is already applied when
         the page renders -- otherwise light-mode visitors see a flash of the
         default dark palette on every navigation. */
      ;(function () {{
        var theme = null
        try {{
          theme = localStorage.getItem('theme')
        }} catch (e) {{
          /* no persistence available */
        }}
        if (!theme) {{
          theme = window.matchMedia('(prefers-color-scheme: light)').matches
            ? 'light'
            : 'dark'
        }}
        if (theme === 'light') {{
          document.documentElement.setAttribute('data-theme', 'light')
        }}
      }})()
    </script>
  </head>
  <body>
    <button id="theme-toggle" type="button" aria-label="Switch to light mode">
      <svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </svg>
      <svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
      </svg>
    </button>

    <!-- One shared metal ramp, referenced by both layouts. userSpaceOnUse means
         each square samples the ramp at its own coordinates, so squares in
         different years catch different highlights; reflect tiles it down the
         page; the drift makes it read as metal rather than flat yellow. -->
    <svg width="0" height="0" aria-hidden="true" style="position:absolute">
      <defs>
        <linearGradient id="metal" gradientUnits="userSpaceOnUse"
          spreadMethod="reflect" x1="0" y1="0" x2="230" y2="290">
          <stop offset="0%" stop-color="var(--metal-1)" />
          <stop offset="22%" stop-color="var(--metal-2)" />
          <stop offset="40%" stop-color="var(--metal-3)" />
          <stop offset="58%" stop-color="var(--metal-4)" />
          <stop offset="80%" stop-color="var(--metal-5)" />
          <stop offset="100%" stop-color="var(--metal-2)" />
          <animateTransform attributeName="gradientTransform" type="translate"
            values="-230 0;230 0;-230 0" dur="20s" repeatCount="indefinite" />
        </linearGradient>
      </defs>
    </svg>

    <main>
      <p class="eyebrow"><a href="/">&larr; Peter Miller</a></p>
      <h1>Reading by the numbers</h1>
      <p class="lede">
        Every book finished since 2008, one square at a time.
      </p>

      <div class="summary-card">
        <div class="summary-primary">
          <div class="stat"><div class="num">{total}</div><div class="lbl">books since 2008</div></div>
          <div class="stat"><div class="num"><span class="dot"></span>{five}</div><div class="lbl">five stars</div></div>

          <!-- CSS-only view switch, driven by the URL fragment so the five-star
               view is linkable as /reading/#five-stars. The track and knob are
               a single element that animates via `body:has(#five-stars:target)`;
               the two anchors are invisible hit areas layered over it, one of
               which is hidden at any time. (A checkbox would animate the same
               way but could not be linked to, and would disagree with the hash
               if someone arrived on one.) -->
          <div class="switchwrap">
            <span class="switchtrack" aria-hidden="true"
              ><span class="knob"></span
            ></span>
            <span class="switchlbl">5 stars only</span>
            <a class="hit to-list" href="#five-stars"
              aria-label="Show only five-star books"></a>
            <a class="hit to-mosaic" href="#"
              aria-label="Show all books"></a>
          </div>
        </div>
      </div>

      <section class="hero" aria-label="Book mosaic">
        {svg_wide}
        {svg_narrow}
        <p class="hint">Click or tap a square for the book, author, and month.</p>
      </section>

      <!-- Readout bar. Selecting a square prints its book here, on desktop and
           touch alike; hidden until something is selected. -->
      <p class="readout" id="readout" role="status" aria-live="polite">
        <span id="readout-text"></span>
      </p>

      <section class="list-view" id="five-stars" aria-label="Five-star books by year">
        {list_html}
      </section>

      <footer>
        Last book: <time datetime="{last_date_iso}">{last_date}</time>
      </footer>
    </main>

    <script>
      /* The theme itself is applied by the inline script in <head>; this only
         wires up the toggle. */
      ;(function () {{
        var root = document.documentElement
        var btn = document.getElementById('theme-toggle')
        function isLight() {{ return root.getAttribute('data-theme') === 'light' }}
        function label() {{
          btn.setAttribute(
            'aria-label',
            isLight() ? 'Switch to dark mode' : 'Switch to light mode'
          )
        }}
        label()
        btn.addEventListener('click', function () {{
          var next = isLight() ? 'dark' : 'light'
          if (next === 'light') {{
            root.setAttribute('data-theme', 'light')
          }} else {{
            root.removeAttribute('data-theme')
          }}
          try {{ localStorage.setItem('theme', next) }} catch (e) {{}}
          label()
        }})
      }})()

      /* Readout. Selecting a square prints its book into the bar at the bottom
         -- the same interaction on desktop and touch, rather than a native
         hover tooltip the phone could never reach.

         Only the wide layout carries data-b labels. Both layouts emit the same
         books in the same order, so a narrow square is looked up in the (hidden
         but present) wide layout at the same index, which keeps ~1,383
         duplicate strings out of the file. */
      ;(function () {{
        var wide = document.querySelector('svg.wide')
        var narrow = document.querySelector('svg.narrow')
        var out = document.getElementById('readout')
        var text = document.getElementById('readout-text')
        if (!wide || !out || !text) return

        var wideRects = wide.getElementsByTagName('rect')
        var selected = null

        function clear() {{
          if (selected) selected.classList.remove('sel')
          selected = null
          out.classList.remove('show')
          text.textContent = ''
        }}

        function bookFor(rect, svg) {{
          var own = rect.getAttribute('data-b')
          if (own) return own
          var i = Array.prototype.indexOf.call(svg.getElementsByTagName('rect'), rect)
          var twin = wideRects[i]
          return twin ? twin.getAttribute('data-b') : null
        }}

        function wire(svg) {{
          if (!svg) return
          svg.addEventListener('click', function (e) {{
            var rect = e.target.closest ? e.target.closest('rect') : null
            if (!rect) return clear() // clicking the gutter dismisses

            var book = bookFor(rect, svg)
            if (!book) return clear()

            if (selected) selected.classList.remove('sel')
            rect.classList.add('sel')
            selected = rect
            text.textContent = book
            out.classList.add('show')
          }})
        }}

        wire(wide)
        wire(narrow)

        document.addEventListener('keydown', function (e) {{
          if (e.key === 'Escape') clear()
        }})
      }})()
    </script>
  </body>
</html>
"""


def main():
    books = read_books()
    years = by_year(books)
    five = sum(1 for b in books if b[3])

    # The footer date comes from the data, not the clock: it is the last book
    # finished, so regenerating unchanged data yields a byte-identical file.
    last = books[-1][0]  # read_books() sorts ascending

    html = HTML.format(
        total=f"{len(books):,}",
        five=f"{five:,}",
        svg_wide=build_svg(years, PER_ROW_WIDE, wide=True),
        svg_narrow=build_svg(years, PER_ROW_NARROW, wide=False),
        list_html=build_list(years),
        last_date=fmt_long(last),
        last_date_iso=last.isoformat(),
    )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)

    lo, hi = min(years), max(years)
    print(f"Wrote {OUT}")
    print(f"  {len(books)} books, {lo}-{hi} ({len(years)} years)")
    print(f"  {five} five-star ({100 * five / len(books):.1f}%)")
    print(f"  busiest year: {max(years, key=lambda y: len(years[y]))} "
          f"({max(len(v) for v in years.values())} books)")
    print(f"  size: {os.path.getsize(OUT) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
