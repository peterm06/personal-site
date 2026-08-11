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
- `workouts.html` — the fitness page (`/workouts`), a day-level workout
  calendar. **Generated** — see below; do not hand-edit.

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

The `workouts.html` calendar adds its own vars (`--otf`, `--cp`, `--empty`) —
one flat color per era, defined in both themes. Edit those in the generator, not
the output.

## The workouts page (generated)

`workouts.html` is produced by [`scripts/gen_workouts.py`](scripts/gen_workouts.py)
from the CSVs in `data/fitness/`:

- `otf_workouts_full.csv` — Orangetheory sessions (dates, splat points, …)
- `cp_classes.csv` — CorePower classes (append new rows here over time)
- `otf_annotations.csv` — injury/closure notes (present but not rendered)

The hero is a GitHub-style day-level calendar: one block per year (newest on
top), seven day-of-week rows by ~53 week columns, one square per day. Color
marks the era only — flat `--otf` for Orangetheory, flat `--cp` for CorePower —
not intensity. A summary card above it carries the totals. The whole SVG scales
to the page width (no horizontal scroll).

The SVG is **pre-rendered** into the HTML so the page works with no JS.
Regenerate whenever the CSVs change (e.g. new CorePower classes):

```bash
python3 scripts/gen_workouts.py
```

To change colors, geometry, or copy, edit the generator and re-run — never edit
`workouts.html` directly, as it is overwritten.

## Previewing

Just open the file — there is no server to run:

```bash
open index.html
```

(or `open workouts.html`). Any static file server works too, e.g.
`python3 -m http.server`, but it is not required.

## Conventions

- Match the existing file's formatting: 2-space indentation, single quotes in JS.
- Keep pages self-contained and dependency-free; don't introduce a build tool.
- When adding a page, reuse the palette variables and the theme-toggle block.
