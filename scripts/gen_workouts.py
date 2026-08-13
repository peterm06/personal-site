#!/usr/bin/env python3
"""Generate workouts/index.html from the CSVs in data/fitness/.

A day-level calendar heatmap in the GitHub-contributions style: one block per
year (newest on top), seven day-of-week rows by ~53 week columns, one square per
day. Color marks the era, not intensity -- flat accent for Orangetheory, a
different flat accent for CorePower. A single summary card above the calendar
carries the totals.

The page is pre-rendered (the SVG is baked into the HTML) so it works with no
JavaScript and no build step. Re-run this whenever cp_classes.csv gets new rows:

    python3 scripts/gen_workouts.py

It reads:  data/fitness/otf_workouts_full.csv
           data/fitness/cp_classes.csv
and writes: workouts/index.html

The directory-plus-index layout is deliberate: it serves at the clean URL
/workouts on any static host (including plain file servers and GitHub Pages)
without needing extensionless-URL rewriting.
"""

import csv
import datetime as dt
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "fitness")
OUT = os.path.join(ROOT, "workouts", "index.html")

YEAR_MIN, YEAR_MAX = 2018, 2026

# --- geometry (SVG user units; the SVG scales to its container via viewBox) ---
CELL = 11
COL_W = 14          # week-column pitch
ROW_H = 14          # day-row pitch
WEEKS = 54          # max week columns in a year (0..53)
PAD_L = 3           # small left margin (year label sits above each block now)
PAD_T = 4
YEAR_LABEL_H = 24   # space above each block for the year heading
MONTH_LABEL_H = 15  # space above the grid for month labels
BLOCK_GAP = 18      # space between year blocks
BLOCK_H = 7 * ROW_H
HEAD_H = YEAR_LABEL_H + MONTH_LABEL_H
BLOCK_STRIDE = HEAD_H + BLOCK_H + BLOCK_GAP

N_YEARS = YEAR_MAX - YEAR_MIN + 1
SVG_W = PAD_L + WEEKS * COL_W + 6
SVG_H = PAD_T + N_YEARS * (HEAD_H + BLOCK_H) + (N_YEARS - 1) * BLOCK_GAP + 6

# --- narrow layout: each year wraps into rows of a few months ---
M_PER_ROW = 4                      # months per row on narrow screens
M_COLS = 6                         # max week-columns a month can span
M_SLOT_W = M_COLS * COL_W + 12     # horizontal slot per month
M_ROW_STRIDE = MONTH_LABEL_H + BLOCK_H + 12
M_ROWS = 12 // M_PER_ROW           # month-rows per year
M_YEAR_H = YEAR_LABEL_H + M_ROWS * M_ROW_STRIDE
M_SVG_W = PAD_L + M_PER_ROW * M_SLOT_W - 6
M_SVG_H = PAD_T + N_YEARS * (M_YEAR_H + BLOCK_GAP) - BLOCK_GAP + 6

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def parse_date(s):
    return dt.date.fromisoformat(s.strip())


def dow_sun(d):
    """Day of week with Sunday = 0 (GitHub calendar convention)."""
    return (d.weekday() + 1) % 7


def read_otf():
    """Returns (set of workout days, class count, total splat points)."""
    days = set()
    count = 0
    splat = 0
    dates = []
    with open(os.path.join(DATA, "otf_workouts_full.csv")) as f:
        for r in csv.DictReader(f):
            d = parse_date(r["workout_date"])
            days.add(d)
            dates.append(d)
            count += 1
            try:
                splat += int(r["splat_points"])
            except (ValueError, KeyError):
                pass
    return days, dates, count, splat


def read_cp():
    """Returns (set of class days, list of dates, family tallies)."""
    days = set()
    dates = []
    fams = {}
    with open(os.path.join(DATA, "cp_classes.csv")) as f:
        for r in csv.DictReader(f):
            d = parse_date(r["date"])
            days.add(d)
            dates.append(d)
            fams[r["class_family"]] = fams.get(r["class_family"], 0) + 1
    return days, dates, fams


def build_svg(otf_days, cp_days):
    # newest year on top, oldest at the bottom
    years = list(range(YEAR_MAX, YEAR_MIN - 1, -1))

    parts = [
        f'<svg class="heatmap heatmap-wide" viewBox="0 0 {SVG_W} {SVG_H}" '
        f'role="img" preserveAspectRatio="xMinYMin meet" '
        f'aria-label="A calendar of workout days, one block per year from 2026 '
        f'(top) down to 2018 (bottom). Each square is a day: Orangetheory days '
        f'2018 through 2023 in one color, CorePower days 2023 to 2026 in '
        f'another.">'
    ]

    for yi, year in enumerate(years):
        block_top = PAD_T + yi * BLOCK_STRIDE
        grid_top = block_top + HEAD_H
        jan1 = dt.date(year, 1, 1)
        end = dt.date(year, 12, 31)
        start_dow = dow_sun(jan1)

        # year heading, above the block
        parts.append(
            f'<text class="ylabel" x="{PAD_L}" y="{block_top + YEAR_LABEL_H - 6}">{year}</text>'
        )

        # month labels at the column where each month begins
        for m in range(1, 13):
            di = (dt.date(year, m, 1) - jan1).days
            col = (di + start_dow) // 7
            x = PAD_L + col * COL_W
            parts.append(f'<text class="mlabel" x="{x}" y="{grid_top - 5}">{MONTHS[m - 1]}</text>')

        # one square per day
        d = jan1
        while d <= end:
            di = (d - jan1).days
            col = (di + start_dow) // 7
            row = (di + start_dow) % 7
            x = PAD_L + col * COL_W
            y = grid_top + row * ROW_H
            fill, cls = cell_attrs(d, otf_days, cp_days)
            parts.append(
                f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" '
                f'height="{CELL}" rx="2.5" fill="{fill}"/>'
            )
            d += dt.timedelta(days=1)

    parts.append("</svg>")
    return "\n      ".join(parts)


def cell_attrs(d, otf_days, cp_days):
    if d in otf_days:
        return "var(--otf)", "cell otf"
    if d in cp_days:
        return "var(--cp)", "cell cp"
    return "var(--empty)", "cell empty"


def build_svg_mobile(otf_days, cp_days):
    """Narrow-screen variant: each year wraps into rows of M_PER_ROW months."""
    years = list(range(YEAR_MAX, YEAR_MIN - 1, -1))

    parts = [
        f'<svg class="heatmap heatmap-narrow" viewBox="0 0 {M_SVG_W} {M_SVG_H}" '
        f'role="img" preserveAspectRatio="xMinYMin meet" '
        f'aria-label="A calendar of workout days, one block per year from 2026 '
        f'(top) down to 2018 (bottom), each year wrapped into rows of '
        f'{M_PER_ROW} months. Each square is a day: Orangetheory days 2018 '
        f'through 2023 in one color, CorePower days 2023 to 2026 in another.">'
    ]

    for yi, year in enumerate(years):
        year_top = PAD_T + yi * (M_YEAR_H + BLOCK_GAP)
        parts.append(
            f'<text class="ylabel" x="{PAD_L}" y="{year_top + YEAR_LABEL_H - 6}">{year}</text>'
        )

        for m in range(1, 13):
            slot = (m - 1) % M_PER_ROW
            mrow = (m - 1) // M_PER_ROW
            ox = PAD_L + slot * M_SLOT_W
            oy = year_top + YEAR_LABEL_H + mrow * M_ROW_STRIDE
            grid_top = oy + MONTH_LABEL_H

            parts.append(f'<text class="mlabel" x="{ox}" y="{oy + MONTH_LABEL_H - 5}">{MONTHS[m - 1]}</text>')

            first = dt.date(year, m, 1)
            nxt = dt.date(year + (m == 12), m % 12 + 1, 1)
            start_dow = dow_sun(first)
            d = first
            while d < nxt:
                di = (d - first).days
                col = (di + start_dow) // 7
                row = (di + start_dow) % 7
                x = ox + col * COL_W
                y = grid_top + row * ROW_H
                fill, cls = cell_attrs(d, otf_days, cp_days)
                parts.append(
                    f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" '
                    f'height="{CELL}" rx="2.5" fill="{fill}"/>'
                )
                d += dt.timedelta(days=1)

    parts.append("</svg>")
    return "\n      ".join(parts)


def fmt_range(dates):
    lo, hi = min(dates), max(dates)
    return lo.strftime("%b %Y"), hi.strftime("%b %Y")


def fmt_long(d):
    """'August 11, 2026' -- strftime('%-d') is not portable, so build it here."""
    return f"{d.strftime('%B')} {d.day}, {d.year}"


HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Fitness — Peter Miller</title>
    <meta
      name="description"
      content="A running tally of my workouts across CorePower and Orangetheory, as a calendar."
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

        /* calendar: one flat accent per era */
        --empty: #1b212b;
        --otf: #45b892;
        --cp: #9a7be0;
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

        --empty: #e2e5e9;
        --otf: #2a9a76;
        --cp: #7e58c4;
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
        max-width: 60rem;
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
      }}

      /* --- the calendar hero --- */
      .hero {{
        margin-top: 2rem;
      }}
      .heatmap-wrap {{
        max-width: 54rem;
      }}

      footer {{
        margin-top: 3rem;
        color: var(--muted);
        font-size: 0.8rem;
        opacity: 0.8;
      }}
      svg.heatmap {{
        display: block;
        width: 100%;
        height: auto;
      }}
      .heatmap .mlabel {{
        font-family: 'Atkinson Hyperlegible', sans-serif;
        font-size: 9px;
        fill: var(--muted);
      }}
      .heatmap .ylabel {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 17px;
        fill: var(--muted);
      }}
      .heatmap .cell {{
        stroke: rgba(0, 0, 0, 0.18);
        stroke-width: 0.5;
      }}
      [data-theme='light'] .heatmap .cell {{
        stroke: rgba(0, 0, 0, 0.06);
      }}

      /* --- two calendar layouts: wide (one strip per year) and narrow
             (each year wrapped into rows of a few months) --- */
      svg.heatmap-narrow {{ display: none; }}

      @media (max-width: 600px) {{
        .summary-card {{
          width: 100%;
        }}
        .summary-primary {{
          justify-content: center;
          text-align: center;
          gap: 1.25rem 2.5rem;
        }}
        .summary-primary .stat:first-child {{
          flex-basis: 100%;
        }}
        svg.heatmap-wide {{ display: none; }}
        svg.heatmap-narrow {{ display: block; }}
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
      <p class="eyebrow"><a href="/">&larr; Peter Miller</a></p>
      <h1>Fitness by the numbers</h1>
      <p class="lede">
        Every workout since 2018, one square at a time.
      </p>

      <div class="summary-card">
        <div class="summary-primary">
          <div class="stat"><div class="num">{total}</div><div class="lbl">total since 2018</div></div>
          <div class="stat"><div class="num"><span class="dot" style="background:var(--cp)"></span>{cp_count}</div><div class="lbl">CorePower</div></div>
          <div class="stat"><div class="num"><span class="dot" style="background:var(--otf)"></span>{otf_count}</div><div class="lbl">Orangetheory</div></div>
        </div>
      </div>

      <section class="hero" aria-label="Workout calendar">
        <div class="heatmap-wrap">
      {svg_wide}
      {svg_narrow}
        </div>
      </section>

      <footer>
        Last class: <time datetime="{last_date_iso}">{last_date}</time>
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
    </script>
  </body>
</html>
"""


def main():
    otf_days, otf_dates, otf_count, otf_splat = read_otf()
    cp_days, cp_dates, fams = read_cp()

    # The footer date comes from the data, not the clock: it is the most recent
    # class of either era, so regenerating unchanged data yields an identical
    # file. Taken from the union rather than assuming CorePower is always last.
    last = max(otf_days | cp_days)

    html = HTML.format(
        svg_wide=build_svg(otf_days, cp_days),
        svg_narrow=build_svg_mobile(otf_days, cp_days),
        total=f"{otf_count + len(cp_dates):,}",
        otf_count=f"{otf_count:,}",
        cp_count=f"{len(cp_dates):,}",
        last_date=fmt_long(last),
        last_date_iso=last.isoformat(),
    )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)
    otf_lo, otf_hi = fmt_range(otf_dates)
    cp_lo, cp_hi = fmt_range(cp_dates)
    print(f"Wrote {OUT}")
    print(f"  OTF: {otf_count} classes ({len(otf_days)} days), {otf_lo}-{otf_hi}")
    print(f"  CP:  {len(cp_dates)} classes ({len(cp_days)} days), {cp_lo}-{cp_hi}")
    print(f"  Total classes: {otf_count + len(cp_dates)}")


if __name__ == "__main__":
    main()
