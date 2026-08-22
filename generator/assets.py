"""Image handling: the headshot and post figures.

Both machines this site is authored from get the same commands here, so the
platform-specific resize recipes no longer have to live in prose: macOS `sips`
is used when present and ImageMagick `convert` otherwise.
"""

import shutil
import subprocess

from . import config
from .report import warn


def _tool():
    """Return 'sips', 'convert', or None depending on what is installed."""
    if shutil.which('sips'):
        return 'sips'
    if shutil.which('convert'):
        return 'convert'
    return None


def _run(cmd, src, dst, tool):
    result = subprocess.run(
        [str(c) for c in cmd], capture_output=True, text=True)
    if result.returncode != 0:
        warn(f"{tool} failed to resize {src}: {result.stderr.strip()}")
        return False
    return True


def source_width(src):
    """Pixel width of an image, or None if it cannot be determined."""
    if shutil.which('sips'):
        out = subprocess.run(['sips', '-g', 'pixelWidth', str(src)],
                             capture_output=True, text=True)
        for line in out.stdout.splitlines():
            if 'pixelWidth:' in line:
                return int(line.split(':')[1].strip())
    elif shutil.which('identify'):
        out = subprocess.run(['identify', '-format', '%w', str(src)],
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip().isdigit():
            return int(out.stdout.strip())
    return None


def resize_longest_edge(src, dst, max_px):
    """Shrink so the longest edge is max_px, keeping the source format."""
    tool = _tool()
    if tool == 'sips':
        cmd = ['sips', '-Z', max_px, src, '--out', dst]
    elif tool == 'convert':
        # ">" only shrinks — never upscales a photo that is already small.
        cmd = ['convert', src, '-resize', f'{max_px}x{max_px}>',
               '-quality', '85', dst]
    else:
        return None
    return tool if _run(cmd, src, dst, tool) else None


def resize_to_width(src, dst, max_px, quality=82):
    """Downscale to max_px wide and re-encode as JPEG. Never upscales."""
    tool = _tool()
    width = source_width(src)
    if width is not None and width <= max_px:
        max_px = width  # already small enough; re-encode without upscaling

    if tool == 'sips':
        cmd = ['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', quality,
               '--resampleWidth', max_px, src, '--out', dst]
    elif tool == 'convert':
        cmd = ['convert', src, '-resize', f'{max_px}x>',
               '-quality', quality, dst]
    else:
        return None
    return tool if _run(cmd, src, dst, tool) else None


def generate_headshot():
    """Regenerate the web-sized headshot from content/headshot.jpeg.

    Skips gracefully (with a note) if the source photo or both tools are
    missing, so page generation never fails on account of the image.

    Note this rewrites headshot_web.jpg on every run, so the re-encode shows up
    as a binary diff even when the source photo has not changed --
    `git checkout headshot_web.jpg` if that was not intended.
    """
    src, dst = config.HEADSHOT_SRC, config.HEADSHOT_WEB
    if not src.exists():
        print(f"Note: {src} not found — skipping headshot resize "
              f"({dst.name} is still what index.html expects).")
        return

    tool = resize_longest_edge(src, dst, config.HEADSHOT_MAX_PX)
    if tool:
        print(f"Wrote {dst.name} (resized from {src.name} with {tool}, "
              f"max {config.HEADSHOT_MAX_PX}px)")
    elif _tool() is None:
        print("Note: neither `sips` nor ImageMagick `convert` is available — "
              f"skipping headshot resize. Resize {src.name} to "
              f"{config.HEADSHOT_MAX_PX}px manually and save as {dst.name}.")


def add_figure(slug, path):
    """Downscale `path` into images/<slug>/ for use in a post.

    Returns the repo-root-relative path to reference from the Markdown.
    """
    if not path.exists():
        raise SystemExit(f"Error: {path} not found.")
    if _tool() is None:
        raise SystemExit(
            "Error: neither `sips` nor ImageMagick `convert` is available.")

    dest_dir = config.IMAGES_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dst = dest_dir / f'{path.stem}.jpg'

    tool = resize_to_width(path, dst, config.FIGURE_MAX_PX)
    if not tool:
        raise SystemExit(f"Error: {tool} could not resize {path}.")

    rel = dst.relative_to(config.ROOT)
    print(f"Wrote {rel} ({dst.stat().st_size // 1024} KB, "
          f"max {config.FIGURE_MAX_PX}px wide, via {tool})")
    print(f"\nReference it from the post as:\n\n    ![Caption]({rel})\n"
          f"    **Caption shown under the figure.**\n")
    return rel


def warn_large_images():
    """Warn about any committed image big enough to bloat the repo.

    The nitf_io source PNG is 34 MB; a copy of one like it must never be
    committed in place of a downscaled version.
    """
    if not config.IMAGES_DIR.exists():
        return
    for path in sorted(config.IMAGES_DIR.rglob('*')):
        if path.is_file() and path.stat().st_size > config.IMAGE_WARN_BYTES:
            mb = path.stat().st_size / 1_000_000
            warn(f"{path.relative_to(config.ROOT)} is {mb:.1f} MB — downscale it "
                 f"with `build.py --image {path.parent.name} <source>`")
