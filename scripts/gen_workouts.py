#!/usr/bin/env python3
"""Generate workouts.html from the CSVs in data/fitness/.

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
and writes: workouts.html  (served at /workouts)
"""

import csv
import datetime as dt
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "fitness")
OUT = os.path.join(ROOT, "workouts.html")

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
        f'<svg class="heatmap" viewBox="0 0 {SVG_W} {SVG_H}" '
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
            if d in otf_days:
                fill, cls = "var(--otf)", "cell otf"
            elif d in cp_days:
                fill, cls = "var(--cp)", "cell cp"
            else:
                fill, cls = "var(--empty)", "cell empty"
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

      * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }}

      html {{
        height: 100%;
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
        padding: 1.5rem 1.75rem;
        display: grid;
        gap: 1.25rem;
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

      /* --- theme toggle (same as index) --- */
      #theme-toggle {{
        position: fixed;
        top: 1.25rem;
        right: 1.25rem;
        width: 2.5rem;
        height: 2.5rem;
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
        A running log of my fitness classes since 2018.
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
      {svg}
        </div>
      </section>
    </main>

    <script>
      ;(function () {{
        var root = document.documentElement
        var btn = document.getElementById('theme-toggle')
        function stored() {{ try {{ return localStorage.getItem('theme') }} catch (e) {{ return null }} }}
        function store(theme) {{ try {{ localStorage.setItem('theme', theme) }} catch (e) {{}} }}
        function apply(theme) {{
          if (theme === 'light') {{
            root.setAttribute('data-theme', 'light')
            btn.setAttribute('aria-label', 'Switch to dark mode')
          }} else {{
            root.removeAttribute('data-theme')
            btn.setAttribute('aria-label', 'Switch to light mode')
          }}
        }}
        var initial = stored()
        if (!initial) {{
          initial = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
        }}
        apply(initial)
        btn.addEventListener('click', function () {{
          var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light'
          apply(next)
          store(next)
        }})
      }})()
    </script>
  </body>
</html>
"""


def main():
    otf_days, otf_dates, otf_count, otf_splat = read_otf()
    cp_days, cp_dates, fams = read_cp()

    svg = build_svg(otf_days, cp_days)

    html = HTML.format(
        svg=svg,
        total=f"{otf_count + len(cp_dates):,}",
        otf_count=f"{otf_count:,}",
        cp_count=f"{len(cp_dates):,}",
    )

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
