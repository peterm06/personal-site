# CLAUDE.md

Personal site for Peter Miller — a small, hand-authored static site. No framework,
no bundler, no dependencies at runtime.

## Philosophy: single-file pages

Each page is one self-contained `.html` file at the repo root. CSS lives in a
`<style>` block in the `<head>`; the only JavaScript is a tiny inline theme
toggle. There is **no build step** — files are served as-is. Fonts (Fraunces +
Atkinson Hyperlegible) are the one external dependency, loaded from Google Fonts.

Pages:

- `index.html` — the landing page (name + profile links), served at `/`.
- `workouts/index.html` — the fitness page, a day-level workout calendar.
  **Generated** — see below; do not hand-edit.
- `reading/index.html` — the reading page, a book mosaic. **Generated** — see
  below; do not hand-edit.

The directory-plus-index layout on subpages is deliberate: it yields clean
`/workouts` and `/reading` URLs on any static host without extensionless-URL
rewriting. Link to them **with the trailing slash** (`/reading/`) — `/reading`
301s to `/reading/`, and a redirect makes the browser skip the view transition.

Pages navigate with **cross-document view transitions** (`@view-transition`,
plus `view-transition-name: theme-toggle` so the fixed toggle does not
cross-fade with the page). This is CSS-only and additive — unsupported browsers
just navigate instantly — but it requires `http(s)`, so it does not appear over
`file://`.

Two things to leave alone here:

- **Don't pair mismatched elements with a shared `view-transition-name`.** A
  morph between the landing `h1` (480×72, 54px, gradient) and a subpage
  back-link (91×23, 14px, muted) was tried and reverted: snapshots are rasters
  stretched into one animating box, so aspect ratios that far apart visibly
  squash and ghost the text. Pair elements of similar size and shape, or not at
  all.
- **`scrollbar-gutter: stable` on `html` is load-bearing.** The landing page
  does not scroll and subpages do, so without it a scrollbar appears mid-
  navigation and shifts the centred content and the fixed toggle sideways.

## Palette & theming

Colors are CSS custom properties on `:root` (dark, the default) with overrides
under `[data-theme='light']`. Keep both themes in sync when adding a variable.

Core palette (shared by every page):

| var           | role                                    |
| ------------- | --------------------------------------- |
| `--ink`       | page background                         |
| `--paper`     | primary text                            |
| `--muted`     | secondary text, labels, dividers-ish    |
| `--hairline`  | borders / dividers                      |
| `--jade`, `--sky`, `--indigo`, `--violet` | the iridescent accent ramp (used in the animated name gradient and per-link hues) |

Theme selection: an inline script reads `localStorage.theme`, falling back to
`prefers-color-scheme`. The toggle button sets/removes `data-theme='light'` on
`<html>`. Copy this block verbatim into any new page so theming stays consistent.

The workouts calendar adds its own vars (`--otf`, `--cp`, `--empty`) —
one flat color per era, defined in both themes. Edit those in the generator, not
the output.

The reading mosaic adds `--book` (an ordinary book) and `--metal-1..5` plus
`--metal-flat` (the five-star gold ramp). `index.html` carries flat `--gold` and
`--book` too, so its teaser squares match the page they link to.

## The workouts page (generated)

`workouts/index.html` is produced by [`scripts/gen_workouts.py`](scripts/gen_workouts.py)
from the CSVs in `data/fitness/`:

- `otf_workouts_full.csv` — Orangetheory sessions (dates, splat points, …)
- `cp_classes.csv` — CorePower classes (append new rows here over time)
- `otf_annotations.csv` — injury/closure notes (present but not rendered)

The hero is a GitHub-style day-level calendar: one block per year (newest on
top), one square per day. Color marks the era only — flat `--otf` for
Orangetheory, flat `--cp` for CorePower — not intensity. A summary card above
it carries the totals. The generator emits **two** pre-rendered SVGs — a wide
layout (one ~53-week strip per year) and a narrow one (each year wrapped into
rows of 4 months) — and a `max-width: 600px` media query swaps between them,
so the page is responsive with no JS and no horizontal scroll.

The SVG is **pre-rendered** into the HTML so the page works with no JS.
Regenerate whenever the CSVs change (e.g. new CorePower classes):

```bash
python3 scripts/gen_workouts.py
```

To change colors, geometry, or copy, edit the generator and re-run — never edit
`workouts/index.html` directly, as it is overwritten.

## The reading page (generated)

`reading/index.html` is produced by [`scripts/gen_reading.py`](scripts/gen_reading.py)
from `data/reading/storygraph_export.csv` (a StoryGraph account export; replace
the file wholesale and re-run):

```bash
python3 scripts/gen_reading.py
```

One small square per book, in finish order, grouped into a block per year
(newest on top), wrapping at a fixed number per row so no row spans the page.
Color is categorical like the workouts page — five stars versus everything else,
never a scale. Same two-SVG responsive trick (40 books per row wide, 24 narrow).

Three things here are load-bearing:

- **The metal is one gradient, not 227.** A gradient inside a 10px square is
  invisible, so a single `<linearGradient>` in `userSpaceOnUse` coordinates
  spans the whole grid and every five-star square samples it at its own
  position. That positional variation is what reads as metal. It also drifts via
  SMIL, echoing the `<h1>` sheen.
- **The two metal ramps are not the same shape.** Dark mode gets a bright
  specular highlight; on light paper that highlight would vanish, so light mode
  keeps the ramp in a narrow mid-dark band and gets its metallic quality from
  saturation instead. Light mode's `--book` is also lightened so five stars
  separate by value as well as hue — hue alone fails for colourblind readers.
  Both ramps keep a high floor on purpose: the variation is decorative, so no
  square should look dim enough to imply it is *less* of a five-star.
- **Hover tooltips are native `<title>` children, wide layout only.** Zero JS.
  The narrow layout omits them because touch screens have no hover, which also
  keeps ~150 KB out of the file.

## Previewing

`open index.html` is fine for most work, but two things only behave correctly
over `http(s)`: the `/workouts` URL and the view transitions. To see the site as
deployed, serve it:

```bash
python3 -m http.server 8000
```

Then visit <http://localhost:8000>. (`.claude/launch.json` defines this as the
`static` preview server.)

## Conventions

- Match the existing file's formatting: 2-space indentation, single quotes in JS.
- Keep pages self-contained and dependency-free; don't introduce a build tool.
- When adding a page, reuse the palette variables and the theme-toggle block.
