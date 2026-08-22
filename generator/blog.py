"""Blog posts: one Markdown file in, one HTML page out.

A post is a single file, content/posts/<slug>.md, whose YAML front matter
carries the metadata:

    ---
    title: A 2D CFAR Detector with Intel IPP
    date: 2026-08-18
    tags: [Signal Processing, C++, Intel IPP]
    repo: https://github.com/dennisfgardner/2D_ipp_CFAR
    excerpt: >
      Finding small, bright clusters of pixels ...
    ---

Everything else is derived: the slug is the filename, the index order is the
date, and whether the page loads Prism or KaTeX is detected from the rendered
body rather than declared by hand.
"""

import datetime
import html
import re

import markdown
import yaml

from . import config
from .layout import page, page_title, tags_html
from .report import warn

REQUIRED_KEYS = ('title', 'date')

_FRONT_MATTER_RE = re.compile(r'\A---[ \t]*\n(.*?\n)---[ \t]*\n', re.DOTALL)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def split_front_matter(text, path):
    """Return (metadata dict, body). Warns and returns ({}, text) if absent."""
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        warn(f"{path.name} has no YAML front matter — add a --- block with "
             f"at least {', '.join(REQUIRED_KEYS)}")
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    # lstrip so a blank line after the front matter cannot change the Markdown.
    return meta, text[m.end():].lstrip('\n')


def as_date(value):
    """Normalise a front-matter date to a datetime.date for sorting.

    YAML yields a date for `2026-08-18` and a datetime if a time is attached;
    anything else (a hand-written "August 18, 2026") is not comparable to
    either, so it sorts last instead of raising mid-build.
    """
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return datetime.date.min


def format_date(value, path):
    """Front-matter dates are real dates (2026-08-18); display them long-form.

    Built from the components rather than strftime('%-d') because the
    no-zero-pad flag is not portable.
    """
    if hasattr(value, 'year'):
        return f'{value:%B} {value.day}, {value.year}'
    if value is not None:
        warn(f"{path.name}: date {value!r} is not a real date — "
             f"write it as YYYY-MM-DD so posts sort correctly")
    return '' if value is None else str(value)


def load_posts():
    """Read every content/posts/*.md into a post dict, newest first."""
    posts = []
    for path in sorted(config.POSTS_DIR.glob('*.md')):
        meta, body = split_front_matter(
            path.read_text(encoding='utf-8'), path)

        for key in REQUIRED_KEYS if meta else ():
            if not meta.get(key):
                warn(f"{path.name} front matter is missing '{key}'")

        content = render_markdown(body)
        check_images(content, path)

        posts.append({
            'slug': path.stem,
            'title': meta.get('title', path.stem),
            'date': meta.get('date'),
            'date_display': format_date(meta.get('date'), path),
            'tags': meta.get('tags') or [],
            'repo': meta.get('repo'),
            'excerpt': meta.get('excerpt') or first_paragraph(content),
            'html': content,
        })

    # Newest first. A post with an unusable date sorts last, never crashes.
    posts.sort(key=lambda p: as_date(p['date']), reverse=True)
    return posts


def first_paragraph(content):
    """Plain-text first paragraph, used when a post declares no excerpt."""
    m = re.search(r'<p>(.*?)</p>', content, re.DOTALL)
    if not m:
        return ''
    return html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()


def check_images(content, path):
    """Warn about figures a post references but that are not on disk."""
    for src in re.findall(r'<img [^>]*src="([^"]+)"', content):
        if src.startswith(('http://', 'https://', 'data:')):
            continue
        if not (config.ROOT / src).exists():
            warn(f"{path.name} references {src}, which does not exist")


# ---------------------------------------------------------------------------
# Markdown -> HTML
# ---------------------------------------------------------------------------

def render_markdown(text):
    """Convert a post body to HTML, then promote its images to <figure>."""
    body = markdown.markdown(
        text,
        extensions=config.MD_EXTENSIONS,
        extension_configs=config.MD_EXTENSION_CONFIGS)
    return wrap_figures(body)


# A paragraph holding nothing but an image, optionally followed by a paragraph
# that is entirely bold — the caption convention the Markdown sources use.
_FIGURE_RE = re.compile(
    r'<p>(<img [^>]*?/?>)</p>'
    r'(?:\s*<p><strong>(.*?)</strong></p>)?',
    re.DOTALL)


def wrap_figures(html_body):
    """Turn image-only paragraphs into <figure>, absorbing a following all-bold
    paragraph as the <figcaption>.

    Markdown has no figure syntax, so posts write a caption as a bold line
    directly under the image. Converting here keeps the Markdown sources plain
    (and re-syncable from an upstream README) instead of littered with raw HTML.
    """
    def replace(m):
        img, caption = m.group(1), m.group(2)
        if caption:
            return (f'<figure>{img}\n'
                    f'<figcaption>{caption.strip()}</figcaption></figure>')
        return f'<figure>{img}</figure>'
    return _FIGURE_RE.sub(replace, html_body)


# ---------------------------------------------------------------------------
# Per-post CDN assets
# ---------------------------------------------------------------------------

def post_assets(post):
    """Return (head_extra, scripts), loading Prism and KaTeX only where the
    rendered body actually contains code or math.

    Detected rather than declared: fenced code always emits
    <code class="language-...">, and pymdownx.arithmatex in generic mode always
    emits class="arithmatex". A post with neither ships zero JavaScript.
    """
    head, scripts = [], []
    content = post['html']

    if '<code class="language-' in content:
        head.append(
            f'    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/'
            f'prism/{config.PRISM_VERSION}/themes/prism.min.css">')
        # The autoloader resolves language files relative to its own URL unless
        # told otherwise, which 404s on a CDN — hence the explicit path.
        scripts.append(
            f'    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/'
            f'{config.PRISM_VERSION}/components/prism-core.min.js"></script>\n'
            f'    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/'
            f'{config.PRISM_VERSION}/plugins/autoloader/prism-autoloader.min.js"\n'
            f'        data-autoloader-path="https://cdnjs.cloudflare.com/ajax/libs/'
            f'prism/{config.PRISM_VERSION}/components/"></script>')

    if 'class="arithmatex"' in content:
        head.append(
            f'    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/'
            f'katex@{config.KATEX_VERSION}/dist/katex.min.css">')
        # Delimiters match arithmatex's generic output (see config.MD_EXTENSIONS).
        scripts.append(
            f'    <script defer src="https://cdn.jsdelivr.net/npm/katex@{config.KATEX_VERSION}'
            f'/dist/katex.min.js"></script>\n'
            f'    <script defer src="https://cdn.jsdelivr.net/npm/katex@{config.KATEX_VERSION}'
            f'/dist/contrib/auto-render.min.js"\n'
            f'        onload="renderMathInElement(document.body, {{delimiters: ['
            f'{{left: String.raw`\\[`, right: String.raw`\\]`, display: true}}, '
            f'{{left: String.raw`\\(`, right: String.raw`\\)`, display: false}}]}});">'
            f'</script>')

    return '\n'.join(head), '\n'.join(scripts)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def post_url(post):
    return f"blog-{post['slug']}.html"


def render_blog(posts):
    """blog.html — the index: one card per post, no bodies."""
    cards = []
    for post in posts:
        cards.append(f'''        <article class="post-card">
            <h3 class="post-card-title"><a href="{post_url(post)}">{html.escape(post['title'])}</a></h3>
            <span class="blog-date">{html.escape(post['date_display'])}</span>
            <p class="post-excerpt">{html.escape(post['excerpt'])}</p>
{tags_html(post['tags'], 12)}
            <a class="post-readmore" href="{post_url(post)}">Read more &rarr;</a>
        </article>''')

    cards_html = '\n\n'.join(cards) if cards else (
        '        <p class="blog-intro">No posts yet.</p>')

    body = f'''    <div class="container">
        <h2>Blog</h2>
        <p class="blog-intro">Thoughts on physics, AI, and systems engineering.</p>

{cards_html}
    </div>'''

    return page(page_title('Blog'), 'blog', body)


def render_post(post):
    """blog-<slug>.html — one full post."""
    head_extra, scripts = post_assets(post)

    repo = post.get('repo')
    repo_html = f'''
            <p class="post-source">Source code:
                <a href="{repo}" target="_blank" rel="noopener">{html.escape(repo)}</a></p>''' if repo else ''

    body = f'''    <div class="container">
        <a class="post-back" href="blog.html">&larr; Blog</a>

        <article class="blog-post">
            <div class="blog-header">
                <h1>{html.escape(post['title'])}</h1>
                <span class="blog-date">{html.escape(post['date_display'])}</span>
            </div>

{tags_html(post['tags'], 12)}

            <div class="blog-content">
{post['html']}
            </div>{repo_html}
        </article>
    </div>'''

    return page(page_title(post['title']), 'blog', body, head_extra, scripts)
