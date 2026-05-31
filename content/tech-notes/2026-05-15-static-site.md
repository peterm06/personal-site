+++
title = "Picking a static site generator"
date = 2026-05-15
+++

I wanted a personal site that loads fast, stays simple to maintain, and keeps my content in plain Markdown that I'm not locked into.

The shortlist came down to a single-binary generator versus a Node-based one. The deciding factors were repo cleanliness and how little framework-specific scaffolding ends up checked in.

```toml
# config lives in one small file
title = "Peter"
compile_sass = false
```

The publish flow is the same regardless: write Markdown, open a pull request, review the deploy preview, merge, and the live site rebuilds on its own.
