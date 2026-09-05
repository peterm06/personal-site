# Peter Miller - Personal Site

My personal site, built with help from Claude.

## Pages

- `index.html` — landing page (`/`): name, profile links, contact info
- `workouts/index.html` — fitness calendar (`/workouts`). **Generated — do not
  hand-edit.**
- `reading/index.html` — book mosaic (`/reading`). **Generated — do not
  hand-edit.**

## Regenerating the reading page

`reading/index.html` is built from a StoryGraph export. To update, replace the
export and re-run:

```bash
python3 scripts/gen_reading.py
```

Export from StoryGraph (Manage Account → Export), then save it over
`data/reading/storygraph_export.csv`.

## Regenerating the workouts page

`workouts/index.html` (including its pre-rendered SVG calendars) is built from
the CSVs in `data/fitness/` by a small Python script (stdlib only, no
dependencies):

```bash
python3 scripts/gen_workouts.py
```

Re-run it whenever the data changes — e.g. after appending new rows to
`data/fitness/cp_classes.csv`. The script overwrites `workouts/index.html` in
place; commit the regenerated file along with the data change.

CorePower doesn't offer a CSV export, so to add new classes you can either
manually append rows to `data/fitness/cp_classes.csv`, or give a recent
screenshot of the app's Class History screen to an agent like Claude and it
can update the CSV for you.

To tweak the page itself (colors, geometry, copy), edit
`scripts/gen_workouts.py` and re-run — changes made directly to
`workouts/index.html` are lost on the next regeneration.

## Previewing

Opening `index.html` directly works for most things, but the cross-page
**view transitions need `http(s)`** — over `file://` navigations just cut. To
see the site as deployed, serve it:

```bash
python3 -m http.server 8000
```

Then visit <http://localhost:8000>. This also exercises the real `/workouts`
URL, which `file://` cannot.

## History: how the workouts data was originally assembled

The initial `otf_workouts_full.csv` and `cp_classes.csv` weren't exported from
either app directly — Orangetheory and CorePower don't offer a clean data
export. Instead, years of class-confirmation emails from both services were
gathered and parsed into CSVs, giving a full history of classes going back to 2018. Classes since then have been added incrementally, via CSV exports where
available and screenshot transcription otherwise (see above).
