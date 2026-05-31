# Deploying to Cloudflare Pages from GitHub

This site is plain static output from Zola, so deployment is: push to GitHub,
let Cloudflare Pages build it on every commit, and serve it from Cloudflare's
CDN. Pull requests get their own preview URLs automatically.

There is one Cloudflare-specific gotcha (Zola isn't in their newer build image);
it's covered under Troubleshooting and is a two-click fix.

---

## 1. Put the site in a GitHub repo

From inside the project folder (the one with `config.toml`):

```sh
git init
git add .
git commit -m "Initial site"
```

Create an empty repo on GitHub (no README/license, to avoid a merge), then:

```sh
git branch -M main
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

`public/` is already in `.gitignore`, so only source is committed.

## 2. Connect Cloudflare Pages to the repo

1. Sign in at dash.cloudflare.com.
2. In the left nav choose **Workers & Pages**, then **Create** → **Pages** tab → **Connect to Git** (also called "Import an existing Git repository").
3. Authorize GitHub if prompted and select your repo.
4. Set the **production branch** to `main`.
5. Enter a **project name** — note this becomes your free URL, `your-project-name.pages.dev`.

## 3. Build settings

1. For **Framework preset**, choose **Zola**. This auto-fills:
   - **Build command:** `zola build`
   - **Build output directory:** `public`
2. Expand **Environment variables (advanced)** and add one:
   - Name: `ZOLA_VERSION`
   - Value: the version you run locally. Check with `zola --version` and use that exact number (for example `0.21.0`).

   Pin it to your local version deliberately — Zola occasionally renames config
   keys between releases, so matching versions avoids the build passing locally
   but failing in CI (or vice versa).
3. Click **Save and Deploy**.

The first build runs `zola build` and publishes `public/` to your `*.pages.dev`
subdomain.

## 4. Set your base URL

After the first deploy you have a real URL. Put it in `config.toml` so absolute
links, feeds, and sitemaps are correct:

```toml
base_url = "https://your-project-name.pages.dev"
```

Commit and push; Cloudflare rebuilds automatically.

### Keep preview URLs working (recommended)

Branch/PR previews are served from different URLs than production, which can
break asset links if `base_url` is hardcoded. To handle both, replace the build
command in the Pages settings with:

```sh
if [ "$CF_PAGES_BRANCH" = "main" ]; then zola build; else zola build --base-url $CF_PAGES_URL; fi
```

Production uses your real `base_url`; previews use their own generated URL.

## 5. Custom domain (optional)

In the Pages project → **Custom domains** → **Set up a custom domain**, enter
your domain. If the domain's DNS is already on Cloudflare, the record is created
for you; otherwise follow the CNAME instructions shown. Then update `base_url`
in `config.toml` to the custom domain and push.

---

## Your day-to-day workflow

1. Create a branch and write a Markdown file in `content/tech-notes/` or
   `content/five-stars/` (front matter: `title` and `date`).
2. Push the branch and open a pull request on GitHub.
3. Cloudflare posts a **preview URL** on the PR — open it to see the rendered post.
4. Merge the PR. Cloudflare rebuilds `main` and the live site updates in a minute
   or two.

No build files live in the repo and there's no GitHub Actions workflow to
maintain — Cloudflare handles the build.

---

## Troubleshooting

**`zola: not found` / `Exited with error code: 127`.** Cloudflare's v2 build
image does not include Zola. Fix it in the Pages project: **Settings** →
**Build** → **Build system version**, switch to **version 1**, and redeploy.
(Version 1 includes Zola; `ZOLA_VERSION` then selects which release.)

**`unknown field` / `invalid type` TOML error in the build log.** Your
`ZOLA_VERSION` differs from the version the config was written/tested against.
Set `ZOLA_VERSION` to match your local `zola --version`. The error message lists
the valid field names for that version, so any needed change is a quick rename.

**Fonts or styles missing on a preview URL only.** You hardcoded `base_url` and
didn't add the conditional build command from step 4 — add it.

**Old content still showing.** Cloudflare caches aggressively. Confirm the
deployment finished in the Pages dashboard; a hard refresh (or a cache purge in
the Cloudflare dashboard) clears stale assets.
