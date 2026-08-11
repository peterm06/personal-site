# Peter Miller - Personal Site

My personal site. Hand-authored static HTML — no framework, no build step.
Open `index.html` in a browser to preview.

## Pages

- `index.html` — landing page (`/`)
- `workouts.html` — fitness calendar (`/workouts`). **Generated — do not
  hand-edit.**

## Regenerating the workouts page

`workouts.html` (including its pre-rendered SVG calendars) is built from the
CSVs in `data/fitness/` by a small Python script (stdlib only, no
dependencies):

```bash
python3 scripts/gen_workouts.py
```

Re-run it whenever the data changes — e.g. after appending new rows to
`data/fitness/cp_classes.csv`. The script overwrites `workouts.html` in place;
commit the regenerated file along with the data change.

To tweak the page itself (colors, geometry, copy), edit
`scripts/gen_workouts.py` and re-run — changes made directly to
`workouts.html` are lost on the next regeneration.
