# Personal site — Zola starter

A clean, content-forward personal site: CV, Colophon, 5 Stars, and Tech Notes.
Single readable column, Atkinson Hyperlegible Next, light/dark theme.

## Run locally

Install Zola (https://www.getzola.org/documentation/getting-started/installation/),
then:

```sh
zola serve
```

Open http://127.0.0.1:1111. The dev server hot-reloads on save.

To build the production site into `public/`:

```sh
zola build
```

## Layout

```
config.toml            site config (one file)
content/               your Markdown
  _index.md            home
  cv.md                /cv/
  colophon.md          /colophon/
  five-stars/          /five-stars/   (one .md per entry)
  tech-notes/          /tech-notes/   (one .md per entry)
templates/             Tera layouts (base, index, section, page)
static/                served as-is (css, js)
public/                build output (git-ignored)
```

## Add a post

Drop a Markdown file in `content/tech-notes/` or `content/five-stars/`:

```
+++
title = "My new note"
date = 2026-06-01
+++

Body text in Markdown.
```

## Deploy (Netlify or Cloudflare Pages)

Connect this repo and set:

- **Build command:** `zola build`
- **Publish directory:** `public`
- **Environment variable:** `ZOLA_VERSION` = a recent version, e.g. `0.19.2`

Every push to `main` publishes; every pull request gets its own preview URL.

## Notes

- Fonts load from Google Fonts in `templates/base.html`. To self-host, download
  the woff2 files (OFL licensed), drop them in `static/fonts/`, and swap the
  `<link>` for `@font-face` rules in `static/css/style.css`.
- The CV prints cleanly to PDF — open `/cv/` and use the browser's Print to PDF.
  The `@media print` block strips nav, footer, and color.
