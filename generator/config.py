"""Paths, third-party versions, and the hand-edited site configuration.

Everything the generator needs to locate a file or a CDN asset lives here, so
no other module hardcodes a path.
"""

from pathlib import Path

import yaml

# Repo root: the directory build.py lives in. All *served* paths are relative to
# it, because Cloudflare serves the repo root directly with no build step.
ROOT = Path(__file__).resolve().parent.parent

CONTENT = ROOT / "content"
POSTS_DIR = CONTENT / "posts"
CV_PATH = CONTENT / "cv.tex"
SITE_YAML = CONTENT / "site.yaml"

# Output goes to the repo root alongside the assets the pages reference.
OUT = ROOT
IMAGES_DIR = ROOT / "images"
STYLESHEET = "styles.css"

# Headshot: source photo (drop a new one in) and the web-sized copy index.html
# references. The web copy is regenerated on every run.
HEADSHOT_SRC = CONTENT / "headshot.jpeg"
HEADSHOT_WEB = ROOT / "headshot_web.jpg"
HEADSHOT_MAX_PX = 600  # longest edge of the web copy

# Post figures are downscaled to this width by `build.py --image`.
FIGURE_MAX_PX = 1600

# Warn about any committed image larger than this. The nitf_io repo's source
# PNG is 34 MB; a copy of it must never land in images/.
IMAGE_WARN_BYTES = 1_000_000

# CDN assets, pulled in per-post by blog.post_assets() and never site-wide.
PRISM_VERSION = "1.29.0"
KATEX_VERSION = "0.16.11"

# Markdown -> HTML for blog post bodies.
#   fenced_code         emits <pre><code class="language-bash">, which is both
#                       what Prism reads and how post_assets() detects code.
#   pymdownx.arithmatex converts $...$/$$...$$ to \(...\)/\[...\] at build time.
#                       Doing the math pass here rather than in the browser
#                       means python-markdown's code-span/fence protection
#                       applies, so a shell variable like $IPPROOT inside a
#                       ```bash block is never mistaken for math. KaTeX is
#                       configured with the matching delimiters in post_assets().
MD_EXTENSIONS = [
    "fenced_code",
    "tables",
    "attr_list",
    "sane_lists",
    "smarty",
    "pymdownx.arithmatex",
]
MD_EXTENSION_CONFIGS = {
    "pymdownx.arithmatex": {"generic": True},
}


def load_site():
    """Return the parsed content/site.yaml (name, footer year, stats, thesis)."""
    with open(SITE_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)
