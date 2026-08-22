"""Build warnings.

The generator never fails a build over content problems -- it collects them here
and build.py prints them at the end. The point is that silent breakage becomes
loud: before this existed, a renamed CV section rendered an empty page with no
indication anything was wrong.
"""

import sys

WARNINGS = []


def warn(message):
    """Record a build warning to be reported at the end of the run."""
    WARNINGS.append(message)


def flush():
    """Print the collected warnings to stderr. Returns how many there were."""
    # stdout is block-buffered when piped while stderr is not, so without this
    # the warnings surface above the build output they refer to.
    sys.stdout.flush()
    if WARNINGS:
        print(f"\n{len(WARNINGS)} warning(s):", file=sys.stderr)
        for message in WARNINGS:
            print(f"  ! {message}", file=sys.stderr)
    return len(WARNINGS)
