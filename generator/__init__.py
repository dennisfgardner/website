"""Static site generator for dennisfgardner.com.

The site is plain HTML with no client-side framework and no build step in
hosting: Cloudflare serves this repo's files directly, so the generated pages
are committed and this package runs locally (see build.py at the repo root).

    config  paths, versions, and content/site.yaml
    latex   parsing content/cv.tex into structured data
    layout  the shared page chrome (nav, footer, <head>)
    pages   the CV-derived pages and the thesis page
    blog    Markdown posts -> blog.html + one page per post
    assets  image resizing (headshot and post figures)
"""
