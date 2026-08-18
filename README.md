# Website

This website is hosted on Cloudflare (free tier). Cloudflare is linked to the GitHub repo
and updates with every push — it serves the files in this repo directly and runs no build
step, so the generated HTML and images are committed.

The pages are generated from `CV_ver19_20260706.tex`, `blog_posts.py`, and the Markdown in
`posts/` by `cv_to_html.py`. Do not hand-edit the `.html` files.

## Setup

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Regenerate and preview

```bash
venv/bin/python cv_to_html.py
python3 -m http.server 8080
```

See `CLAUDE.md` for the full layout, how to add a blog post, and how to update CV content.
