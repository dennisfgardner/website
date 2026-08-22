# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Overview

A static personal website for Dennis F. Gardner Jr., Ph.D. — physicist / systems engineer /
AI-ML researcher, job-hunting. Plain HTML and CSS, no client-side framework, no build step in
hosting: Cloudflare serves this repo's files directly on every push, so **the generated HTML
and images are committed** and `build.py` runs locally.

## Layout

Sources in `content/`, code in `generator/`, everything served at the repo root.

```
content/            sources, hand-edited
  cv.tex              the CV → index/about/publications/contact
  site.yaml           site name, footer year, citation stats, thesis block
  posts/<slug>.md     a blog post: YAML front matter + Markdown body
  headshot.jpeg       source photo (not served)
generator/          code
  config  paths, CDN versions, Markdown extensions, site.yaml loader
  latex   cv.tex → data        layout  shared <head>/nav/footer
  pages   CV + thesis pages    blog    posts → blog.html + a page each
  assets  image resizing       report  build warnings
styles.css          all styling; render_* emit HTML and class names, never CSS
images/<slug>/      post figures
```

**Every `.html` at the repo root is generated — never hand-edit one.** Change the source and
rerun the build.

## Build

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt   # once
venv/bin/python build.py
python3 -m http.server 8080
```

`venv/` is gitignored and does not travel between machines, so a `ModuleNotFoundError` means
rerun the `pip install` — not recreate the venv. Cloudflare runs none of this, so commit the
regenerated pages along with the sources.

The build never fails on a content problem. It collects warnings — a CV section that stopped
matching, a figure a post references but that is missing, front matter missing a key, an image
over 1 MB — and prints them after the summary. **Read them**; each means a page came out wrong.

## Blog posts

One file per post, `content/posts/<slug>.md`. The slug is the filename, the index order is the
`date`, and Prism/KaTeX load only where `post_assets()` finds `<code class="language-` or
`class="arithmatex"` in the rendered body — none of that is declared by hand.

```bash
venv/bin/python build.py --new-post my-post        # scaffolds the .md + images/my-post/
venv/bin/python build.py --image my-post fig.png   # downscale a figure into images/my-post/
```

Front matter:

- **`title`** *(required)* — the `<h1>` and tab title, so **no `# H1` in the body**
  (markdownlint MD041 complains about this; ignore it)
- **`date`** *(required)* — `YYYY-MM-DD`; sorts the index, renders as "August 18, 2026"
- **`tags`** — `[Signal Processing, C++]`
- **`repo`** — URL for the "Source code" line at the foot of the post
- **`excerpt`** — index-card teaser; falls back to the post's first paragraph

Image paths are relative to the **repo root**, where the generated HTML lives, not to the
`.md`. `--image` picks `sips` or `convert` per platform, writes a 1600 px JPEG, and never
upscales. Deleting a post's `.md` deletes its `blog-<slug>.html` on the next build.

Three conventions not to break:

- **Math** — `pymdownx.arithmatex` converts `$...$` at *build* time. Keep it there:
  python-markdown's fence protection is what stops a shell variable like `$IPPROOT` in a
  ```` ```bash ```` block from being eaten as math.
- **Code** — Prism's autoloader needs an explicit `data-autoloader-path` on a CDN or grammars
  404 silently; `post_assets()` sets it.
- **Figures** — Markdown has no figure syntax, so a caption is one bold line under the image;
  `wrap_figures()` promotes that pair to `<figure>`/`<figcaption>`.

### Re-syncing a post from its upstream README

`2d-ipp-cfar.md` and `nitf-io.md` are copies of the READMEs of
`github.com/dennisfgardner/{2D_ipp_CFAR,nitf_io}`, edited for publication — the site builds
standalone and never reads those repos. After re-copying, re-apply: the front-matter block,
drop the H1, rewrite image paths and add bold captions, promote bare `./program` invocations
to ```` ```bash ```` fences, then the per-post fixes — CFAR: stale `src/` paths and typos;
NITF: the `-This repo`/`bacause`/`can be build` typos, the un-wrapped `git submodule update`,
the opening paragraph on what NITF is, and the closing repo link.

nitf_io's `output0.png` is 15360x11264 and 34 MB — never commit it; `--image` takes it to
~300 KB.

## CV content

`generator/latex.py` parses the `\section{...}` blocks (`parse_work_experience`,
`parse_education`, `parse_enumerate`, `parse_awards`, `parse_expertise`, tied together by
`parse_cv`).

Sections are matched by **prefix**, so the live count in `\section{Publications -- 19
peer-reviewed, 1,900+ citations, h-index 18}` can be updated freely; a prefix that matches
nothing warns instead of silently emptying a page. Publication and patent counts on the
homepage and in `.pub-stats` are counted from the CV — only the citation total and h-index are
typed by hand, in `site.yaml`.

Each peer-reviewed `\item` ends with `\href{https://doi.org/<DOI>}{link}`, which renders as a
small "link" badge (`.pub-text a`). Follow that convention for new entries.

## Headshot

`assets.generate_headshot()` rewrites `headshot_web.jpg` from `content/headshot.jpeg` (600 px
longest edge) on **every** run, so it shows up as a binary diff even when the photo has not
changed — `git checkout headshot_web.jpg` if that was not intended.
