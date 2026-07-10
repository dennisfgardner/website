# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A static personal website for Dennis F. Gardner Jr., Ph.D. — a physicist/systems engineer/AI-ML researcher who is job-hunting. No build tools, frameworks, or dependencies — pure HTML and CSS.

## Structure

- `index.html` — homepage with intro and links to other pages
- `about.html` — bio, expertise badges, work experience timeline, education, awards
- `publications.html` — 19 peer-reviewed papers, 5 patents, 3 trade articles
- `contact.html` — real contact info (email, phone, Vienna VA, Google Scholar)
- `blog.html` — blog post listings (still contains AI-generated placeholder content)
- `cv_to_html.py` — Python script that parses `CV_ver18_20260706.tex` and regenerates all pages except `blog.html`

All pages share inline CSS. The color scheme is `#2c3e50` (dark blue header/footer), `#34495e` (nav), `#1abc9c` (teal accent), `#f5f5f5` (page background). Nav and footer HTML are duplicated across pages — there is no shared layout file.

Nav order: Home → About → Publications → Contact (blog.html is in the nav too, rendered separately).

## Updating content from the CV

The HTML pages are **generated** from the LaTeX CV — do not edit `index.html`, `about.html`, `contact.html`, or `publications.html` by hand if the intent is to update CV-derived content. Instead:

1. Edit `CV_ver18_20260706.tex`
2. Run `python3 cv_to_html.py`

The script uses only the Python standard library. It parses LaTeX sections delimited by `\section{...}` and writes all four pages. Key parsing functions: `parse_work_experience`, `parse_education`, `parse_enumerate` (for publications/patents), `parse_awards`, `parse_expertise`.

If the CV file is renamed or a new version is used, update `CV_PATH` at the top of `cv_to_html.py`.

## Development

Open any `.html` file directly in a browser, or serve locally:

```bash
python3 -m http.server 8080
```

## What still needs real content

- `blog.html` — still has AI-generated placeholder posts and comments; no parser covers it
