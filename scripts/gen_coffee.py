#!/usr/bin/env python3
"""Generate coffee/index.html from the CSVs in data/coffee/.

A shelf of coffee bags: one small bag per coffee, grouped into a block per year
(newest on top), newest bag first within each year. Each bag is drawn in its
roaster's two colours -- the bag colour behind the roaster's name, the label
colour in a band at the bottom holding the coffee's name -- so every bag from
one roaster matches. Loved bags carry a heart sticker, nope bags a broken-heart sticker and fade back, decaf bags
say so in the band.

The bags are plain HTML, not SVG, so the names are real text: selectable and
findable with Cmd-F. Their gusset shape (folded top, angled corners) is a CSS
clip-path, and the type scales with each bag via container query units.

It reads:  data/coffee/bags.csv      roaster, coffee, drank, rating, decaf, notes
           data/coffee/roasters.csv  roaster, bag, label (hex colours)
and writes: coffee/index.html        (served at /coffee/)

    python3 scripts/gen_coffee.py

`drank` is a year ("2024") or a month ("2024-06"). Exact days are not asked
for: old bags rarely have one. Within a year, bags with a month sort by it and
bags without one keep their row order, so bags.csv is kept oldest first and
new rows are appended at the bottom.
"""

import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAGS = os.path.join(ROOT, "data", "coffee", "bags.csv")
ROASTERS = os.path.join(ROOT, "data", "coffee", "roasters.csv")
OUT = os.path.join(ROOT, "coffee", "index.html")

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
RATINGS = ("nope", "ok", "loved")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# Text on a bag: near-black or near-white when the roaster's other colour does
# not contrast enough with the surface it sits on.
DARK_TEXT = "#1a2028"
LIGHT_TEXT = "#f2f3f5"

HEART = ('<svg class="love" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 '
         '21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.2 0 3.9 1.3 5.2 3 1.3-1.7 '
         '3-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z"/></svg>')


# Loved and nope bags carry a round sticker in the top corner: a heart or a
# broken heart. The sticker is in fixed colours, not the roaster's, so it never
# reads as part of the print, and it sits outside the bag's clip-path so it
# stays bright when a nope bag fades. Ok bags carry nothing.
_HEART_IN_DISC = ('<path class="h" transform="translate(4.6 4.9) scale(.62)" d="M12 '
                  '21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.2 0 3.9 1.3 5.2 3 1.3-1.7 '
                  '3-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z"/>')
STICKERS = {
    "loved": ('<svg class="sticker loved" viewBox="0 0 24 24" aria-hidden="true">'
              '<circle class="disc" cx="12" cy="12" r="11"/>' + _HEART_IN_DISC + '</svg>'),
    "nope": ('<svg class="sticker nope" viewBox="0 0 24 24" aria-hidden="true">'
             '<circle class="disc" cx="12" cy="12" r="11"/>' + _HEART_IN_DISC +
             '<path class="crack" d="M12.3 7.6 10.6 11.2 13.2 13.4 11.5 17.6"/></svg>'),
}


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def fail(path, line, msg):
    sys.exit(f"{os.path.relpath(path, ROOT)}:{line}: {msg}")


def read_roasters():
    """Roaster name (case-insensitive) -> (bag colour, label colour)."""
    roasters = {}
    with open(ROASTERS, newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            name = r["roaster"].strip()
            if not name:
                continue
            bag, label = r["bag"].strip(), r["label"].strip()
            for c in (bag, label):
                if not HEX.match(c):
                    fail(ROASTERS, n, f"{c!r} is not a #rrggbb colour")
            roasters[name.lower()] = (bag.lower(), label.lower())
    return roasters


def read_bags():
    """Every bag as a dict, in file order (oldest first)."""
    bags = []
    with open(BAGS, newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            roaster, coffee = r["roaster"].strip(), r["coffee"].strip()
            if not roaster and not coffee:
                continue
            if not roaster or not coffee:
                fail(BAGS, n, "every bag needs a roaster and a coffee")
            m = re.match(r"^(\d{4})(?:-(\d{1,2}))?$", r["drank"].strip())
            if not m:
                fail(BAGS, n, f"drank {r['drank']!r} should be YYYY or YYYY-MM")
            month = int(m.group(2)) if m.group(2) else 0
            if month > 12:
                fail(BAGS, n, f"drank {r['drank']!r} has no month {month}")
            rating = r["rating"].strip().lower()
            if rating not in RATINGS:
                fail(BAGS, n, f"rating {r['rating']!r} should be one of {', '.join(RATINGS)}")
            bags.append({
                "roaster": roaster,
                "coffee": coffee,
                "year": int(m.group(1)),
                "month": month,
                "rating": rating,
                "decaf": r["decaf"].strip().lower() in ("yes", "y", "true", "1"),
                "notes": r["notes"].strip(),
                "row": n,
            })
    return bags


def lum(hex_):
    """WCAG relative luminance."""
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def text_on(fill, other):
    """The roaster's other colour if it reads on `fill`, else dark or light."""
    if contrast(fill, other) >= 3.2:
        return other
    return DARK_TEXT if lum(fill) > 0.25 else LIGHT_TEXT


def when(b):
    return f"{MONTHS[b['month'] - 1]} {b['year']}" if b["month"] else str(b["year"])


def by_year(bags):
    """Year -> bags, newest first. Within a year: by month (no month counts as
    earliest), ties kept in file order, then the whole year reversed."""
    years = {}
    for b in bags:
        years.setdefault(b["year"], []).append(b)
    for y in years:
        years[y].sort(key=lambda b: (b["month"], b["row"]))
        years[y].reverse()
    return years


def bag_html(b, roasters):
    colours = roasters.get(b["roaster"].lower())
    style = ""
    if colours:
        bag, label = colours
        style = (f' style="--c1:{bag};--c2:{label};'
                 f'--t1:{text_on(bag, label)};--t2:{text_on(label, bag)}"')
    cls = ["bag", b["rating"]] + (["decaf"] if b["decaf"] else [])
    parts = [b["coffee"], b["roaster"], when(b), b["rating"]]
    if b["decaf"]:
        parts.append("decaf")
    label = esc(" · ".join(parts))
    notes = f' data-n="{esc(b["notes"])}"' if b["notes"] else ""
    return (
        f'<li class="{" ".join(cls)}"><button type="button" data-b="{label}"{notes}'
        f' aria-label="{label}"><span class="body"{style}>'
        f'<span class="r">{esc(b["roaster"])}</span>'
        f'<span class="c">{"<span class=dc>Decaf</span>" if b["decaf"] else ""}'
        f'<span class="cn">{esc(b["coffee"])}</span></span>'
        f"</span>{STICKERS.get(b['rating'], '')}</button></li>"
    )


def build_shelf(years, roasters):
    if not years:
        return '<p class="none">No bags yet.</p>'
    blocks = []
    for year in sorted(years, reverse=True):
        bags = years[year]
        loved = sum(b["rating"] == "loved" for b in bags)
        decaf = sum(b["decaf"] for b in bags)
        cls = ["year"] + (["has-loved"] if loved else []) + (["has-decaf"] if decaf else [])

        def count(n, extra=""):
            return f'{n} bag{"s" if n != 1 else ""}{extra}'

        blocks.append(
            f'<section class="{" ".join(cls)}" aria-label="{year}">'
            f'<h2>{year}<span class="yn n-all">{count(len(bags))}</span>'
            f'<span class="yn n-loved">{count(loved, " loved")}</span>'
            f'<span class="yn n-decaf">{count(decaf, " decaf")}</span></h2>'
            f'<ol class="shelf">{"".join(bag_html(b, roasters) for b in bags)}</ol>'
            f"</section>"
        )
    return "\n        ".join(blocks)


HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Coffee — Peter Miller</title>
    <meta
      name="description"
      content="Every bag of coffee, in its roaster's colours."
    />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Peter Miller" />
    <meta property="og:title" content="Coffee — Peter Miller" />
    <meta
      property="og:description"
      content="Every bag of coffee, in its roaster's colours."
    />
    <meta property="og:url" content="https://www.peterhmiller.com/coffee/" />
    <meta property="og:image" content="https://www.peterhmiller.com/og.png" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta
      property="og:image:alt"
      content="Peter Miller, software engineer in Washington, DC."
    />
    <meta name="twitter:card" content="summary_large_image" />
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

        /* the loved switch and heart echo /reading's five-star gold; a bag
           whose roaster has no colours yet falls back to /reading's slate */
        --gold: #d4a24c;
        --book: #3f4d60;
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
        --gold: #96701a;
        --book: #c0c9d3;
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

      /* --- Cross-document view transitions (see CLAUDE.md) --- */
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
      .num svg {{
        width: 18px;
        height: 18px;
        margin-right: 0.45rem;
        fill: var(--gold);
        vertical-align: 0.02em;
      }}

      /* --- filter switches: iOS-style toggles, as on /reading. Each is driven
             by the URL fragment, so /coffee/#loved and /coffee/#decaf are
             linkable; one filter is on at a time because there is one
             fragment. The targets are empty spans whose oversized scroll
             margin keeps the browser from scrolling when they are targeted. */
      .switches {{
        display: flex;
        gap: 1.5rem;
        margin-left: auto; /* pushes them to the far edge of the card */
        align-self: center;
      }}
      .switchwrap {{
        position: relative;
        display: inline-grid;
        justify-items: center;
        gap: 0.4rem;
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
      .hit {{
        position: absolute;
        inset: -4px;
        border-radius: 10px;
      }}
      .hit.off {{ display: none; }}
      .hit:focus-visible {{
        outline: 2px solid var(--indigo);
        outline-offset: 2px;
      }}
      .target {{
        position: absolute;
        scroll-margin-top: 100vh;
      }}

      body:has(#loved:target) .sw-loved .switchtrack {{ background: var(--gold); }}
      body:has(#decaf:target) .sw-decaf .switchtrack {{ background: var(--sky); }}
      body:has(#loved:target) .sw-loved .knob,
      body:has(#decaf:target) .sw-decaf .knob {{
        transform: translateX(19px);
        background: var(--ink);
      }}
      body:has(#loved:target) .sw-loved .switchlbl,
      body:has(#decaf:target) .sw-decaf .switchlbl {{ color: var(--paper); }}
      body:has(#loved:target) .sw-loved .on,
      body:has(#decaf:target) .sw-decaf .on {{ display: none; }}
      body:has(#loved:target) .sw-loved .off,
      body:has(#decaf:target) .sw-decaf .off {{ display: block; }}

      @media (prefers-reduced-motion: reduce) {{
        .knob,
        .switchtrack,
        .switchlbl {{ transition: none; }}
      }}

      /* --- the shelf --- */
      .hero {{
        margin-top: 2.25rem;
      }}
      .year + .year {{ margin-top: 2rem; }}
      .year h2 {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 1.15rem;
        color: var(--muted);
        display: flex;
        align-items: baseline;
        gap: 0.6rem;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid var(--hairline);
      }}
      .year .yn {{
        font-family: 'Atkinson Hyperlegible', sans-serif;
        font-size: 0.75rem;
        font-weight: 400;
        margin-left: auto;
        opacity: 0.75;
      }}
      .n-loved,
      .n-decaf {{ display: none; }}

      .shelf {{
        list-style: none;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
        gap: 1rem 0.9rem;
      }}

      /* filtering: hide what does not match, then any year left empty, and
         swap each year's count for the filtered one */
      body:has(#loved:target) .bag:not(.loved),
      body:has(#decaf:target) .bag:not(.decaf),
      body:has(#loved:target) .year:not(.has-loved),
      body:has(#decaf:target) .year:not(.has-decaf),
      body:has(#loved:target) .n-all,
      body:has(#decaf:target) .n-all {{ display: none; }}
      body:has(#loved:target) .n-loved,
      body:has(#decaf:target) .n-decaf {{ display: inline; }}

      .bag button {{
        display: block;
        width: 100%;
        padding: 0;
        border: 0;
        background: none;
        font: inherit;
        color: inherit;
        text-align: left;
        cursor: pointer;
        border-radius: 3px;
      }}
      .bag button:focus-visible {{
        outline: 2px solid var(--indigo);
        outline-offset: 3px;
      }}

      /* One bag: the roaster's bag colour behind its name, its label colour in
         a band holding the coffee. A gusset bag: folded top, angled corners.
         Type is sized in cqw so it scales with the bag at every width. */
      .body {{
        --c1: var(--book);
        --c2: var(--hairline);
        --t1: var(--paper);
        --t2: var(--paper);
        container-type: inline-size;
        aspect-ratio: 5 / 7;
        position: relative;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        background: var(--c1);
        color: var(--t1);
        clip-path: polygon(7% 0, 93% 0, 100% 4%, 100% 100%, 0 100%, 0 4%);
        box-shadow: inset 0 0 0 1px rgba(127, 127, 127, 0.14);
        transition: opacity 160ms ease;
      }}
      /* the folded top */
      .body::before {{
        content: '';
        position: absolute;
        inset: 0 0 auto;
        height: 13cqw;
        border-bottom: 1px solid rgba(0, 0, 0, 0.3);
        background: rgba(255, 255, 255, 0.07);
      }}
      .body .r {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 15cqw;
        line-height: 1.02;
        padding: 23cqw 9cqw 0;
        text-wrap: balance;
      }}
      .body .c {{
        margin-top: auto;
        min-height: 27%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        background: var(--c2);
        color: var(--t2);
        font-size: 10.5cqw;
        line-height: 1.2;
        padding: 5cqw 9cqw;
      }}
      .body .dc {{
        font-size: 7.5cqw;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 1cqw;
      }}
      /* the rating sticker, top corner */
      .bag button {{ position: relative; }}
      /* a float keeps only the lines beside the sticker clear of it, so a
         long name still uses the full width below */
      .loved .body .r::before,
      .nope .body .r::before {{
        content: '';
        float: right;
        width: 23cqw;
        height: 17cqw;
      }}
      .sticker {{
        position: absolute;
        right: 6%;
        top: 12%;
        width: 23%;
        height: auto;
        aspect-ratio: 1;
        transform: rotate(-8deg);
        filter: drop-shadow(0 1px 1.5px rgba(0, 0, 0, 0.4));
      }}
      .sticker .disc {{ fill: #f2f3f5; }}
      .sticker.loved .h {{ fill: #c9962e; }}
      .sticker.nope .h {{ fill: #6b7480; }}
      .sticker .crack {{
        fill: none;
        stroke: #f2f3f5;
        stroke-width: 1.5;
        stroke-linejoin: round;
      }}
      .nope .body {{
        filter: saturate(0.3);
        opacity: 0.55;
      }}
      .bag button:hover .body,
      .bag button.sel .body {{
        outline: 2px solid var(--paper);
        outline-offset: -2px;
      }}

      .none {{
        color: var(--muted);
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

      /* --- readout: a bar pinned to the bottom, as on /reading --- */
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
      .readout > span {{
        width: 100%;
        max-width: 44rem;
      }}
      #readout-notes {{
        display: block;
        color: var(--muted);
      }}
      body:has(.readout.show) {{ padding-bottom: 8rem; }}

      @media (max-width: 600px) {{
        .summary-card {{ width: 100%; }}
        .summary-primary {{
          justify-content: center;
          text-align: center;
          gap: 1.25rem 2.5rem;
        }}
        .summary-primary .stat:first-child {{ flex-basis: 100%; }}
        .switches {{
          margin-left: 0;
          flex-basis: 100%;
          justify-content: center;
        }}
        .shelf {{ grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); }}
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

    <main>
      <span class="target" id="loved"></span>
      <span class="target" id="decaf"></span>

      <p class="eyebrow"><a href="/">&larr; Peter Miller</a></p>
      <h1>Coffee by the bag</h1>
      <p class="lede">
        Every bag of coffee I've finished, in its roaster's colours.
      </p>

      <div class="summary-card">
        <div class="summary-primary">
          <div class="stat"><div class="num">{total}</div><div class="lbl">bags</div></div>
          <div class="stat"><div class="num">{heart}{loved}</div><div class="lbl">loved</div></div>

          <!-- CSS-only filters, driven by the URL fragment (see the switch
               styles above and /reading's 5-star switch). -->
          <div class="switches">
            <div class="switchwrap sw-loved">
              <span class="switchtrack" aria-hidden="true"
                ><span class="knob"></span
              ></span>
              <span class="switchlbl">Loved only</span>
              <a class="hit on" href="#loved" aria-label="Show only loved bags"></a>
              <a class="hit off" href="#" aria-label="Show all bags"></a>
            </div>
            <div class="switchwrap sw-decaf">
              <span class="switchtrack" aria-hidden="true"
                ><span class="knob"></span
              ></span>
              <span class="switchlbl">Decaf only</span>
              <a class="hit on" href="#decaf" aria-label="Show only decaf bags"></a>
              <a class="hit off" href="#" aria-label="Show all bags"></a>
            </div>
          </div>
        </div>
      </div>

      <section class="hero" aria-label="Coffee bags by year">
        {shelf}
        {hint}
      </section>

      <!-- Readout bar. Selecting a bag prints its details here. -->
      <p class="readout" id="readout" role="status" aria-live="polite">
        <span><span id="readout-text"></span><span id="readout-notes"></span></span>
      </p>

      {footer}
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

      /* Readout. Selecting a bag prints its details, and notes if it has
         any, into the bar at the bottom -- as on /reading. */
      ;(function () {{
        var shelf = document.querySelector('.hero')
        var out = document.getElementById('readout')
        var text = document.getElementById('readout-text')
        var notes = document.getElementById('readout-notes')
        if (!shelf || !out) return
        var selected = null

        function clear() {{
          if (selected) selected.classList.remove('sel')
          selected = null
          out.classList.remove('show')
          text.textContent = ''
          notes.textContent = ''
        }}

        shelf.addEventListener('click', function (e) {{
          var b = e.target.closest ? e.target.closest('button[data-b]') : null
          if (!b) return clear()
          if (selected) selected.classList.remove('sel')
          b.classList.add('sel')
          selected = b
          text.textContent = b.getAttribute('data-b')
          notes.textContent = b.getAttribute('data-n') || ''
          out.classList.add('show')
        }})

        document.addEventListener('keydown', function (e) {{
          if (e.key === 'Escape') clear()
        }})
        /* a filter can hide the selected bag; the bar goes with it */
        window.addEventListener('hashchange', clear)
      }})()
    </script>
  </body>
</html>
"""


def main():
    roasters = read_roasters()
    bags = read_bags()
    years = by_year(bags)
    loved = sum(b["rating"] == "loved" for b in bags)

    missing = sorted({b["roaster"] for b in bags} - {
        b["roaster"] for b in bags if b["roaster"].lower() in roasters})
    for r in missing:
        print(f"  note: no colours for {r!r} in roasters.csv; using the default")

    # The footer comes from the data, not the clock, so regenerating unchanged
    # data yields a byte-identical file.
    footer = ""
    if bags:
        newest = years[max(years)][0]
        footer = f"<footer>Last bag: {when(newest)}</footer>"

    html = HTML.format(
        total=f"{len(bags):,}",
        loved=f"{loved:,}",
        heart=HEART.replace(' class="love"', ""),
        shelf=build_shelf(years, roasters),
        hint=('<p class="hint">Click or tap a bag for the details.</p>'
              if bags else ""),
        footer=footer,
    )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)

    print(f"Wrote {OUT}")
    print(f"  {len(bags)} bags, {loved} loved, "
          f"{sum(b['decaf'] for b in bags)} decaf, {len(roasters)} roasters")
    print(f"  size: {os.path.getsize(OUT) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
