# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A static personal website for Dennis F. Gardner Jr., Ph.D. — a physicist/systems engineer/AI-ML researcher who is job-hunting. No build tools, frameworks, or dependencies — pure HTML and CSS.

## Structure

- `index.html` — homepage with intro and links to other pages
- `about.html` — bio, expertise badges, work experience timeline, education, awards
- `publications.html` — 19 peer-reviewed papers, 5 patents, 3 trade articles
- `contact.html` — real contact info (email, phone, Vienna VA, Google Scholar)
- `blog.html` — blog post listings (generated; content still AI-generated placeholder)
- `styles.css` — **the single source of truth for all site styling** (every page links it)
- `blog_posts.py` — blog post content (titles, dates, bodies, tags, comments)
- `cv_to_html.py` — Python script that parses `CV_ver18_20260706.tex` and `blog_posts.py` and regenerates **all five** HTML pages

All pages link one external stylesheet, `styles.css` — there is no inline CSS. The color scheme is `#0ea5e9` (teal accent), `#111827` (near-black text), `#ffffff` (page background), `#6b7280`/`#374151` (grays), `#f0f9ff` (accent tint on badges/cards). The nav and footer HTML come from the shared `nav()` helper and `FOOTER` constant in `cv_to_html.py`; every page is generated, so there is no duplicated layout markup.

Nav order: Home → About → Publications → Blog → Contact. The current page's nav link gets `class="active"` (styled in `styles.css`).

## Updating content from the CV

**All HTML pages are generated — do not hand-edit `index.html`, `about.html`, `contact.html`, `publications.html`, or `blog.html`.** Regenerating overwrites them. Edit the source instead, then run `python3 cv_to_html.py`:

- **CV-derived content** (index/about/contact/publications) → edit `CV_ver18_20260706.tex`
- **Blog posts** → edit `blog_posts.py` (the `POSTS` list)
- **Styling for any page** → edit `styles.css`

The script uses only the Python standard library. It parses LaTeX sections delimited by `\section{...}` and writes all five pages. Key parsing functions: `parse_work_experience`, `parse_education`, `parse_enumerate` (for publications/patents), `parse_awards`, `parse_expertise`. Blog pages are built by `render_blog()` from `blog_posts.POSTS`.

If the CV file is renamed or a new version is used, update `CV_PATH` at the top of `cv_to_html.py`.

## Changing the look of the site

All styling lives in `styles.css` — change a value there once and it applies across every page. The Python `render_*` functions emit only HTML (body markup + class names); they carry no CSS. If you add a new class in `styles.css`, reference it from the relevant `render_*` function; if you add a whole new page, link `styles.css` via the shared `page()` helper.

## Updating the homepage headshot

`index.html` shows a circular headshot in the Welcome section. It references `headshot_web.jpg`, a web-sized copy that `cv_to_html.py` regenerates from `headshot.jpeg` on every run (via `generate_headshot()`, using the macOS `sips` tool, longest edge `HEADSHOT_MAX_PX` = 600 px). To replace the photo, drop a new `headshot.jpeg` in the repo root and run `python3 cv_to_html.py` — the resize happens automatically. If `sips` or the source photo is missing, the resize is skipped with a note and page generation still succeeds.

## Development

Open any `.html` file directly in a browser, or serve locally:

```bash
python3 -m http.server 8080
```

## What still needs real content

- The blog posts in `blog_posts.py` are still AI-generated placeholder content (posts and comments). Edit `POSTS` there and rerun `python3 cv_to_html.py` to regenerate `blog.html`.

## Future Work

The site is hosted on Cloudflare's free tier, so **client-side JavaScript is allowed** (the original "static HTML/CSS only" assumption was wrong). Two LaTeX-related features are planned. They use **different** strategies on purpose — see the reasoning in each.

### Strategy 1 — Ph.D. thesis: display as a PDF

A thesis is a large, finished, complex document (university class file, custom macros, figures/TikZ, tables, bibliography). Converting it to HTML (Pandoc/LaTeXML) is high-effort and fragile, and would need re-fixing every time the source changes — for no benefit a PDF doesn't already provide. So: **compile once to PDF and present it, don't convert it.**

Implementation outline:

- Compile the thesis `.tex` → `thesis.pdf` with the existing LaTeX toolchain; place the PDF in the repo (e.g. `thesis.pdf`, or a `thesis/` folder). Note: it's a large binary — decide whether to commit it or keep it out of git via `.gitignore` and upload separately.
- Add a generated page: a new `render_thesis()` in `cv_to_html.py` and a `NAV_LINKS` entry (`('thesis.html', 'Thesis', 'thesis')`). Adding it to `NAV_LINKS` auto-wires the nav in both directions across every page. Optionally add an "Explore" card on the homepage (`render_index`).
- Page layout: real HTML for the **title, abstract, and committee/advisor** (good for skimming + SEO), then an **embedded PDF viewer** (a simple `<iframe src="thesis.pdf">`, or PDF.js for a nicer cross-browser viewer), plus a prominent **Download PDF** button/link.
- Add styling for the thesis page to `styles.css` (single source of truth).

### Strategy 2 — Blog: Markdown + LaTeX math (KaTeX) + code highlighting (Prism.js)

Goal is prose + figures + code snippets + equations, read comfortably on any device. A PDF reads badly on phones and loses SEO/links/site styling, so the blog should render **in the page**. But full-LaTeX-document conversion is fragile — and unnecessary. The realization: you don't need full LaTeX, you need **Markdown with LaTeX math**. Write prose/figures/code in Markdown; write **math in LaTeX syntax** (`$...$` inline, `$$...$$` display) and let a JS library render just the math.

Libraries (loaded via CDN, consistent with the existing Google Fonts CDN link):

- **KaTeX** — renders the math. Faster than MathJax; use its `auto-render` extension to scan the page for `$...$` / `$$...$$` after load.
- **Prism.js** — syntax-highlights fenced code blocks (` ```perl `, ` ```python `, etc.) via `language-*` classes on `<pre><code>`.

Implementation outline:

- Author posts as **Markdown** in `blog_posts.py` (the `POSTS` list currently holds pre-rendered HTML `content`; switch it to Markdown source).
- Convert Markdown → HTML at build time in `cv_to_html.py`. This adds a dependency beyond the stdlib — recommended: **`python-markdown`** plus **`pymdown-extensions`**. Use the `pymdownx.arithmatex` extension so `$...$`/`$$...$$` math is emitted as KaTeX-ready spans and **not mangled** by Markdown (a common failure mode — Markdown otherwise eats `_`, `\`, and `*` inside math). Add a `requirements.txt`; the repo already has a `venv/`.
- Load KaTeX + Prism **only on pages that need them** (blog, and any code-snippet page): add an optional `head_extra`/`scripts` parameter to the shared `page()` helper so those CDN `<link>`/`<script>` tags are injected per-page rather than site-wide.
- Style code blocks / KaTeX overrides in `styles.css` as needed (Prism ships a theme; adjust to match the `#0ea5e9` accent).