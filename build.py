#!/usr/bin/env python3
"""Generate the site from content/ into the repo root.

    venv/bin/python build.py                        regenerate every page
    venv/bin/python build.py --new-post <slug>      start a new blog post
    venv/bin/python build.py --image <slug> <file>  add a figure to a post

Cloudflare serves this repo's files directly and never runs this script, so the
generated HTML is committed alongside the sources it came from.
"""

import argparse
import datetime
import sys
from pathlib import Path

from generator import assets, blog, config, latex, pages, report

NEW_POST_TEMPLATE = """---
title: {title}
date: {date}
tags: []
repo:
excerpt: >-
  One or two sentences, shown on the blog index card. Delete this key to use
  the post's first paragraph instead.
---

Write the post here in Markdown. Do not add an `# H1` — the title above becomes
the heading.

Figures go in images/{slug}/; add them with:

    venv/bin/python build.py --image {slug} <file>

Fenced code blocks and $math$ are picked up automatically; nothing to declare.
"""


def build():
    """Render every page and write it to the repo root."""
    try:
        tex = config.CV_PATH.read_text(encoding='utf-8')
    except FileNotFoundError:
        print(f"Error: {config.CV_PATH} not found.", file=sys.stderr)
        return 1

    data = latex.parse_cv(tex)
    posts = blog.load_posts()

    files = {
        'index.html':        pages.render_index(data),
        'about.html':        pages.render_about(data),
        'contact.html':      pages.render_contact(data),
        'publications.html': pages.render_publications(data),
        'thesis.html':       pages.render_thesis(),
        'blog.html':         blog.render_blog(posts),
    }
    for post in posts:
        files[blog.post_url(post)] = blog.render_post(post)

    for name, markup in files.items():
        (config.OUT / name).write_text(markup, encoding='utf-8')
        print(f"Wrote {name}")

    remove_stale_posts(files)

    assets.generate_headshot()
    assets.warn_large_images()

    print(f"\nParsed: {len(data['experience'])} work entries, "
          f"{len(data['publications'])} publications, {len(data['patents'])} patents, "
          f"{len(data['expertise'])} skills, {len(data['awards'])} awards, "
          f"{len(posts)} blog posts")
    report.flush()
    return 0


def remove_stale_posts(files):
    """Delete blog-*.html pages whose Markdown source is gone.

    The generated HTML is committed, so a deleted or renamed post would
    otherwise leave its old page behind at a URL that still resolves.
    """
    for path in sorted(config.OUT.glob('blog-*.html')):
        if path.name not in files:
            path.unlink()
            print(f"Removed {path.name} (no matching post in "
                  f"{config.POSTS_DIR.name}/)")


def new_post(slug):
    """Scaffold content/posts/<slug>.md and its images directory."""
    path = config.POSTS_DIR / f'{slug}.md'
    if path.exists():
        print(f"Error: {path} already exists.", file=sys.stderr)
        return 1

    title = slug.replace('-', ' ').replace('_', ' ').title()
    path.write_text(
        NEW_POST_TEMPLATE.format(
            title=title, date=datetime.date.today().isoformat(), slug=slug),
        encoding='utf-8')
    (config.IMAGES_DIR / slug).mkdir(parents=True, exist_ok=True)

    print(f"Wrote {path.relative_to(config.ROOT)}")
    print(f"Created {(config.IMAGES_DIR / slug).relative_to(config.ROOT)}/")
    print(f"\nEdit the title, tags, and body, then run:\n\n"
          f"    venv/bin/python build.py\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--new-post', metavar='SLUG',
                        help='scaffold a new post at content/posts/SLUG.md')
    parser.add_argument('--image', nargs=2, metavar=('SLUG', 'FILE'),
                        help='downscale FILE into images/SLUG/ for post SLUG')
    args = parser.parse_args()

    if args.new_post:
        return new_post(args.new_post)
    if args.image:
        slug, path = args.image
        assets.add_figure(slug, Path(path))
        return 0
    return build()


if __name__ == '__main__':
    sys.exit(main())
