"""The shared page chrome: <head>, nav, footer.

Every page on the site is generated through page(), so there is no duplicated
layout markup anywhere and no inline CSS -- styles.css is the single source of
truth for styling.
"""

import hashlib
import html
from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def site():
    """The parsed content/site.yaml, read once per run."""
    return config.load_site()


def stylesheet_href():
    """styles.css URL with a content-hash query string, so browsers fetch the
    latest CSS after each regeneration instead of serving a stale cached copy."""
    path = config.ROOT / config.STYLESHEET
    try:
        digest = hashlib.md5(path.read_bytes()).hexdigest()[:8]
        return f'{config.STYLESHEET}?v={digest}'
    except FileNotFoundError:
        return config.STYLESHEET


# The nav links, in order. Each is (href, label, active_key); the active page's
# link gets class="active" so it highlights site-wide. Post pages pass 'blog'.
NAV_LINKS = [
    ('index.html', 'Home', 'home'),
    ('about.html', 'About', 'about'),
    ('publications.html', 'Publications', 'publications'),
    ('blog.html', 'Blog', 'blog'),
    ('thesis.html', 'Thesis', 'thesis'),
    ('contact.html', 'Contact', 'contact'),
]


def nav(active=None):
    """Return the shared <nav>, marking the link whose key == active."""
    link_lines = []
    for href, label, key in NAV_LINKS:
        cls = ' class="active"' if key == active else ''
        link_lines.append(f'            <a href="{href}"{cls}>{label}</a>')
    links = '\n'.join(link_lines)
    return f'''    <nav>
        <a href="index.html" class="nav-brand">{site()['name']}</a>
        <div class="nav-links">
{links}
        </div>
    </nav>'''


def footer():
    return f'''    <footer>
        <p>&copy; {site()['footer_year']} {site()['name']}</p>
    </footer>'''


def page(title, active, body, head_extra='', scripts=''):
    """Wrap body in the shared page chrome.

    head_extra and scripts let a single page pull in assets the rest of the site
    does not need (KaTeX, Prism) -- see blog.post_assets() -- so those CDN
    requests are not paid for site-wide.
    """
    head_extra = f'\n{head_extra}' if head_extra else ''
    scripts = f'\n{scripts}' if scripts else ''
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{stylesheet_href()}">{head_extra}
</head>
<body>
{nav(active)}
{body}
{footer()}{scripts}
</body>
</html>'''


def page_title(page_name=None):
    """Browser-tab title: '<page> – <name>', or just the name for the homepage."""
    return f"{page_name} – {site()['short_name']}" if page_name else site()['name']


def tags_html(tags, indent):
    """The <div class="tags"> block used by both the blog index and post pages."""
    pad = ' ' * indent
    spans = '\n'.join(
        f'{pad}    <span class="tag">{html.escape(t)}</span>' for t in tags)
    return f'{pad}<div class="tags">\n{spans}\n{pad}</div>'
