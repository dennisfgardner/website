# Website

This website is hosted on Cloudflare (free tier). Cloudflare is linked to the GitHub repo
and updates with every push — it serves the files in this repo directly and runs no build
step, so the generated HTML and images are committed.

The pages are generated from `content/` by `build.py`. Do not hand-edit the `.html` files.

## Setup

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Regenerate and preview

```bash
venv/bin/python build.py
python3 -m http.server 8080
```

## Write a blog post

```bash
venv/bin/python build.py --new-post my-post      # scaffold content/posts/my-post.md
venv/bin/python build.py --image my-post fig.png # downscale a figure into images/my-post/
venv/bin/python build.py                         # regenerate
```

See `CLAUDE.md` for the full layout, the front-matter fields, and how to update CV content.
