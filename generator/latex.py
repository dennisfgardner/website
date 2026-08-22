r"""Parse content/cv.tex into the structured data the pages render from.

This is deliberately a set of narrow regexes over the CV's own conventions
rather than a general LaTeX parser: the input is one document written by one
person, and the failure mode that matters (a section that stops matching) is
reported by section() instead of silently producing an empty page.
"""

import re

from .report import warn

# Formatting commands whose braces are removed but whose inner text is kept.
_INLINE_CMDS = [
    'textsc', 'textbf', 'emph', 'textit', 'footnotesize',
    'normalsize', 'small', 'large', 'Large', 'Huge',
]
# Layout commands, stripped the same way outside of publication entries.
_LAYOUT_CMDS = ['centering', 'raggedright', 'noindent']


def strip_cmd(s, cmd):
    r"""Remove \cmd{...} keeping inner text."""
    pattern = re.compile(r'\\' + re.escape(cmd) + r'\{([^{}]*)\}')
    prev = None
    while prev != s:
        prev = s
        s = pattern.sub(r'\1', s)
    return s


def strip_latex(s, authors=False):
    r"""Convert a run of LaTeX to display HTML.

    \href becomes a link and the author's own name stays bold; everything else
    is flattened to text. Pass authors=True for publication entries, where the
    bold name carries a trailing initial or suffix (\textbf{DF Gardner, et al})
    and the layout commands never appear.
    """
    s = s.replace("---", "—").replace("--", "–")
    s = s.replace("``", "“").replace("''", "”").replace("`", "‘").replace("'", "’")
    # Remove comments
    s = re.sub(r'%.*', '', s)
    # Convert \href{url}{text} to HTML links
    s = re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}', r'<a href="\1">\2</a>', s)
    # Keep the author's name bold before the formatting commands are flattened.
    name = r'DF Gardner[^}]*' if authors else r'DF Gardner'
    s = re.sub(r'\\textbf\{(' + name + r')\}', r'<strong>\1</strong>', s)
    # Strip formatting commands (order matters: innermost first via loop)
    for cmd in _INLINE_CMDS if authors else _INLINE_CMDS + _LAYOUT_CMDS:
        s = strip_cmd(s, cmd)
    # Math mode: $\rightarrow$ → →
    s = s.replace(r'$\rightarrow$', '→')
    # LaTeX escaped special chars
    s = s.replace(r'\&', '&').replace(r'\%', '%').replace(r'\_', '_')
    # Remove remaining LaTeX commands
    s = re.sub(r'\\[a-zA-Z]+\*?\{[^{}]*\}', '', s)
    s = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?', ' ', s)
    # Remove stray braces and spacing chars
    s = re.sub(r'[{}]', '', s)
    s = re.sub(r'[ \t]+', ' ', s)
    return s.strip()


# ---------------------------------------------------------------------------
# Section splitter
# ---------------------------------------------------------------------------

def split_sections(tex):
    r"""Return dict of section_name → raw_content."""
    parts = re.split(r'\\section\{([^}]+)\}', tex)
    # parts[0] is preamble/header, then alternating name/content
    result = {'__header__': parts[0]}
    for i in range(1, len(parts), 2):
        name = parts[i].strip()
        content = parts[i+1] if i+1 < len(parts) else ''
        result[name] = content
    return result


def section(sections, prefix):
    r"""Return the content of the section whose title starts with `prefix`.

    Matching on a prefix rather than the full title is what makes the CV safe to
    edit: the publications heading carries a live citation count
    (\section{Publications -- 19 peer-reviewed, 1,900+ citations, ...}), so an
    exact-title lookup silently emptied the publications page every time that
    number was updated. A prefix that matches nothing warns instead of
    returning '' quietly.
    """
    # An escaped ampersand in the .tex ("Awards, Fellowships \& Scholarships")
    # should match a plain one in the prefix.
    for name, content in sections.items():
        if name.replace('\\&', '&').startswith(prefix):
            return content
    warn(f"cv.tex has no section starting with {prefix!r} — "
         f"the page it feeds will be empty")
    return ''


# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------

def parse_header(raw):
    contact = {}
    m = re.search(r'Vienna,\s*VA', raw)
    contact['city'] = 'Vienna, VA' if m else ''
    m = re.search(r'(\d{3}-\d{3}-\d{4})', raw)
    contact['phone'] = m.group(1) if m else ''
    m = re.search(r'\\href\{mailto:([^}]+)\}\{([^}]+)\}', raw)
    if m:
        contact['email'] = m.group(1)
        contact['email_display'] = m.group(2)
    m = re.search(r'\\href\{(https://scholar[^}]+)\}\{([^}]+)\}', raw)
    if m:
        contact['scholar_url'] = m.group(1)
        contact['scholar_display'] = m.group(2)
    return contact


def parse_summary(raw):
    text = re.sub(r'\\vspace\{[^}]+\}', '', raw)
    return strip_latex(text).strip()


def parse_expertise(raw):
    row_re = re.compile(r'\\checkmark\s+(.+?)&\s*\\checkmark\s+(.+?)\\\\', re.DOTALL)
    skills = []
    for m in row_re.finditer(raw):
        skills.append(strip_latex(m.group(1)).strip())
        skills.append(strip_latex(m.group(2)).strip())
    # last row may have only one cell (trailing &)
    last = re.search(r'\\checkmark\s+([^&\\]+)\s*&\s*\\\\', raw)
    if last:
        skills.append(strip_latex(last.group(1)).strip())
    return [s for s in skills if s]


def parse_work_experience(raw):
    jobs = []
    blocks = re.findall(
        r'\\begin\{tabular\}\{rp\{[^}]+\}\}(.+?)\\end\{tabular\}',
        raw, re.DOTALL)
    for block in blocks:
        # Date range
        m = re.search(
            r'\\textsc\{([^}]+)\}--\\textsc\{([^}]+)\}', block)
        if not m:
            m = re.search(r'\\textsc\{([^}]+)\}', block)
            date = strip_latex(m.group(1)) if m else ''
        else:
            date = strip_latex(m.group(1)) + ' – ' + strip_latex(m.group(2))

        # Title and company (first & ... \\)
        first_line = re.search(r'\\textsc\{[^}]+\}--\\textsc\{[^}]+\}\s*&\s*(.+?)\\\\', block, re.DOTALL)
        if not first_line:
            first_line = re.search(r'\\textsc\{[^}]+\}\s*&\s*(.+?)\\\\', block, re.DOTALL)
        title_line = strip_latex(first_line.group(1)).strip() if first_line else ''

        # Department (emph line)
        dept_m = re.search(r'&\s*\\emph\{([^}]+)\}', block)
        dept = strip_latex(dept_m.group(1)).strip() if dept_m else ''

        # Bullets
        bullets = re.findall(r'\\item\s+(.+?)(?=\\item|\\end\{itemize\})', block, re.DOTALL)
        bullets = [strip_latex(b).strip() for b in bullets if strip_latex(b).strip()]

        if date:
            jobs.append({'date': date, 'title': title_line, 'dept': dept, 'bullets': bullets})
    return jobs


def parse_awards(raw):
    # Skip the column spec {l | l} and extract only cell text
    inner = re.search(r'\\begin\{tabular\}\{[^}]+\}(.+?)\\end\{tabular\}', raw, re.DOTALL)
    if not inner:
        return []
    table = inner.group(1)
    cells = re.split(r'&|\\\\', table)
    awards = []
    for c in cells:
        c = strip_latex(c).strip()
        if c:
            awards.append(c)
    return awards


def parse_education(raw):
    # Split the tabular body into lines on \\
    inner = re.search(r'\\begin\{tabular\}\{[^}]+\}(.+?)\\end\{tabular\}', raw, re.DOTALL)
    if not inner:
        return []
    lines = re.split(r'\\\\', inner.group(1))
    degrees = []
    current = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Degree line: starts with \textsc{MONTH} YEAR &
        m = re.match(r'\\textsc\{([^}]+)\}\s+(\d{4})\s*&\s*(.+)', line, re.DOTALL)
        if m:
            if current:
                degrees.append(current)
            month = strip_latex(m.group(1))
            year = m.group(2)
            degree_text = strip_latex(m.group(3)).strip()
            current = {'date': f'{month} {year}', 'line': degree_text, 'note': ''}
        elif current is not None:
            # Note line: & \small\emph{...}
            note_m = re.search(r'&\s*\\small\s*(?:\\emph|\\textit)\{([^}]+)\}', line)
            if not note_m:
                note_m = re.search(r'&\s*\\small\s*(.+)', line)
            if note_m:
                current['note'] = strip_latex(note_m.group(1)).strip()
    if current:
        degrees.append(current)
    return degrees


def parse_enumerate(raw, authors=False):
    r"""Parse an enumerate block into [{'text', 'notes'}], splitting the
    \quad$\rightarrow$ annotations off as notes."""
    items_raw = re.findall(r'\\item\s+(.*?)(?=\\item|\s*\\end\{enumerate\})', raw, re.DOTALL)
    result = []
    for item in items_raw:
        parts = re.split(r'\\quad\s*\$\\rightarrow\$', item)
        main = strip_latex(parts[0], authors=authors).strip()
        annotations = [strip_latex(p).strip() for p in parts[1:] if strip_latex(p).strip()]
        if main:
            result.append({'text': main, 'notes': annotations})
    return result


def parse_cv(tex):
    """Parse the whole CV into the dict the page renderers consume."""
    sections = split_sections(tex)
    return {
        'contact':            parse_header(sections['__header__']),
        'summary':            parse_summary(section(sections, 'Professional Summary')),
        'expertise':          parse_expertise(section(sections, 'Areas of Expertise')),
        'experience':         parse_work_experience(section(sections, 'Work Experience')),
        'awards':             parse_awards(section(sections, 'Awards, Fellowships')),
        'education':          parse_education(section(sections, 'Education')),
        'patents':            parse_enumerate(section(sections, 'Patents')),
        'publications':       parse_enumerate(section(sections, 'Publications'), authors=True),
        'other_publications': parse_enumerate(section(sections, 'Other Publications'), authors=True),
    }
