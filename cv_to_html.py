#!/usr/bin/env python3
"""Parse CV_ver18_20260706.tex and generate website HTML pages."""

import os
import re
import shutil
import subprocess
import sys

CV_PATH = "CV_ver18_20260706.tex"

# Headshot: source photo (drop in a new one to replace) and the web-sized copy
# that index.html references. The web copy is regenerated on each run.
HEADSHOT_SRC = "headshot.jpeg"
HEADSHOT_WEB = "headshot_web.jpg"
HEADSHOT_MAX_PX = 600  # longest edge of the web copy

# ---------------------------------------------------------------------------
# LaTeX cleaning helpers
# ---------------------------------------------------------------------------

def strip_cmd(s, cmd):
    r"""Remove \cmd{...} keeping inner text."""
    pattern = re.compile(r'\\' + re.escape(cmd) + r'\{([^{}]*)\}')
    prev = None
    while prev != s:
        prev = s
        s = pattern.sub(r'\1', s)
    return s

def strip_latex(s):
    s = s.replace("---", "—").replace("--", "–")
    s = s.replace("``", "“").replace("''", "”").replace("`", "‘").replace("'", "’")
    # Remove comments
    s = re.sub(r'%.*', '', s)
    # Convert \href{url}{text} to HTML links
    s = re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}', r'<a href="\1">\2</a>', s)
    # \textbf{DF Gardner} → bold (keep bold for name in pubs)
    s = re.sub(r'\\textbf\{(DF Gardner)\}', r'<strong>\1</strong>', s)
    # Strip formatting commands (order matters: innermost first via loop)
    for cmd in ['textsc', 'textbf', 'emph', 'textit', 'footnotesize',
                'normalsize', 'small', 'large', 'Large', 'Huge',
                'centering', 'raggedright', 'noindent']:
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
    s = s.strip()
    return s

def clean_pub_authors(s):
    """Like strip_latex but preserves <strong>DF Gardner</strong>."""
    s = s.replace("---", "—").replace("--", "–")
    s = s.replace("``", "“").replace("''", "”").replace("`", "‘").replace("'", "’")
    s = re.sub(r'%.*', '', s)
    s = re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}', r'<a href="\1">\2</a>', s)
    # Bold Gardner first
    s = re.sub(r'\\textbf\{(DF Gardner[^}]*)\}', r'<strong>\1</strong>', s)
    for cmd in ['textsc', 'textbf', 'emph', 'textit', 'footnotesize',
                'normalsize', 'small', 'large', 'Large', 'Huge']:
        s = strip_cmd(s, cmd)
    s = s.replace(r'$\rightarrow$', '→')
    s = s.replace(r'\&', '&').replace(r'\%', '%').replace(r'\_', '_')
    s = re.sub(r'\\[a-zA-Z]+\*?\{[^{}]*\}', '', s)
    s = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?', ' ', s)
    s = re.sub(r'[{}]', '', s)
    s = re.sub(r'[ \t]+', ' ', s)
    return s.strip()

# ---------------------------------------------------------------------------
# Section splitter
# ---------------------------------------------------------------------------

def split_sections(tex):
    """Return dict of section_name → raw_content."""
    parts = re.split(r'\\section\{([^}]+)\}', tex)
    # parts[0] is preamble/header, then alternating name/content
    result = {'__header__': parts[0]}
    for i in range(1, len(parts), 2):
        name = parts[i].strip()
        content = parts[i+1] if i+1 < len(parts) else ''
        result[name] = content
    return result

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

def parse_enumerate(raw, pub_mode=False):
    items_raw = re.findall(r'\\item\s+(.*?)(?=\\item|\s*\\end\{enumerate\})', raw, re.DOTALL)
    result = []
    for item in items_raw:
        # Check for → annotation lines
        parts = re.split(r'\\quad\s*\$\\rightarrow\$', item)
        if pub_mode:
            main = clean_pub_authors(parts[0]).strip()
            annotations = [strip_latex(p).strip() for p in parts[1:] if strip_latex(p).strip()]
        else:
            main = strip_latex(parts[0]).strip()
            annotations = [strip_latex(p).strip() for p in parts[1:] if strip_latex(p).strip()]
        if main:
            result.append({'text': main, 'notes': annotations})
    return result

# ---------------------------------------------------------------------------
# Shared HTML pieces
# ---------------------------------------------------------------------------

NAV = '''    <nav>
        <a href="index.html" class="nav-brand">Dennis F. Gardner Jr., Ph.D.</a>
        <div class="nav-links">
            <a href="index.html">Home</a>
            <a href="about.html">About</a>
            <a href="publications.html">Publications</a>
            <a href="blog.html">Blog</a>
            <a href="contact.html">Contact</a>
        </div>
    </nav>'''

FOOTER = '''    <footer>
        <p>&copy; 2025 Dennis F. Gardner Jr., Ph.D.</p>
    </footer>'''

BASE_CSS = '''        *, *::before, *::after { box-sizing: border-box; }
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            line-height: 1.6;
            margin: 0;
            background: #ffffff;
            color: #111827;
        }
        nav {
            position: sticky;
            top: 0;
            z-index: 100;
            background: #ffffff;
            border-bottom: 1px solid #e5e7eb;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
            height: 64px;
        }
        .nav-brand {
            font-weight: 700;
            font-size: 1rem;
            color: #111827;
            text-decoration: none;
            white-space: nowrap;
        }
        .nav-links { display: flex; gap: 0.25rem; }
        .nav-links a {
            color: #374151;
            text-decoration: none;
            padding: 0.4rem 0.75rem;
            border-radius: 6px;
            font-size: 0.9rem;
            font-weight: 500;
            transition: background-color 0.15s, color 0.15s;
        }
        .nav-links a:hover { background: #f3f4f6; color: #0ea5e9; }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 2.5rem 1.5rem 4rem;
        }
        h2 {
            font-size: 1.375rem;
            font-weight: 700;
            color: #111827;
            margin: 0 0 1.5rem 0;
            padding-bottom: 0.4rem;
            border-bottom: 2px solid #0ea5e9;
            display: inline-block;
        }
        h3 { color: #1f2937; margin: 0 0 0.25rem; }
        a { color: #0ea5e9; }
        a:hover { text-decoration: underline; }
        footer {
            background: #f9fafb;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            padding: 1.5rem;
            color: #6b7280;
            font-size: 0.875rem;
            margin-top: 2rem;
        }
        footer p { margin: 0; }
        @media (max-width: 600px) {
            nav {
                height: auto;
                flex-direction: column;
                align-items: flex-start;
                padding: 0.75rem 1rem;
                gap: 0.5rem;
            }
            .nav-links { flex-wrap: wrap; gap: 0 0.1rem; }
            .container { padding: 1.5rem 1rem 3rem; }
        }'''

def page(title, extra_css, nav, body, footer):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
{BASE_CSS}
{extra_css}
    </style>
</head>
<body>
{nav}
{body}
{footer}
</body>
</html>'''

# ---------------------------------------------------------------------------
# render_index
# ---------------------------------------------------------------------------

def render_index(data):
    summary = data['summary']
    first_two = '. '.join(summary.split('. ')[:2]) + '.'

    body = f'''    <div class="container">
        <div class="intro">
            <div class="intro-text">
                <p class="tagline">Physicist &nbsp;·&nbsp; Systems Engineer &nbsp;·&nbsp; AI &amp; ML Researcher</p>
                <h2 class="hero-name">Hi, I&#8217;m Dennis.</h2>
                <p class="hero-summary">{first_two}</p>
                <div class="cta-buttons">
                    <a class="cta-btn cta-btn-primary" href="about.html">About Me</a>
                    <a class="cta-btn cta-btn-secondary" href="publications.html">Publications</a>
                    <a class="cta-btn cta-btn-secondary" href="contact.html">Contact</a>
                </div>
            </div>
            <img class="headshot" src="headshot_web.jpg"
                 alt="Portrait of Dennis F. Gardner Jr.">
        </div>
        <div class="links-section">
            <h2>Explore</h2>
            <ul>
                <li><a href="about.html">About &amp; Experience</a> — background, expertise, and career timeline</li>
                <li><a href="publications.html">Publications &amp; Patents</a> — 19 peer-reviewed papers, 1,900+ citations, h-index 18, and 5 patents</li>
                <li><a href="contact.html">Contact</a> — get in touch</li>
            </ul>
        </div>
    </div>'''

    css = '''        .intro {
            display: flex;
            align-items: center;
            gap: 3rem;
            padding: 3rem 0 2.5rem;
        }
        .intro-text { flex: 1; }
        .tagline {
            color: #6b7280;
            font-size: 0.85rem;
            font-weight: 500;
            margin: 0 0 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }
        .hero-name {
            font-size: 2.25rem;
            font-weight: 700;
            color: #111827;
            margin: 0 0 1rem;
            border: none;
            display: block;
            padding: 0;
        }
        .hero-summary {
            color: #374151;
            font-size: 1rem;
            margin: 0 0 1.5rem;
            line-height: 1.7;
        }
        .headshot {
            width: 190px;
            height: 190px;
            border-radius: 50%;
            object-fit: cover;
            object-position: center 20%;
            flex-shrink: 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .cta-buttons { display: flex; gap: 0.75rem; flex-wrap: wrap; }
        .cta-btn {
            display: inline-block;
            padding: 0.6rem 1.25rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.15s;
        }
        .cta-btn-primary { background: #0ea5e9; color: white; }
        .cta-btn-primary:hover { background: #0284c7; text-decoration: none; color: white; }
        .cta-btn-secondary { background: #f3f4f6; color: #374151; }
        .cta-btn-secondary:hover { background: #e5e7eb; text-decoration: none; color: #111827; }
        .links-section ul { list-style: none; padding: 0; }
        .links-section li {
            padding: 0.875rem 0;
            border-bottom: 1px solid #f3f4f6;
            font-size: 0.95rem;
            color: #374151;
        }
        .links-section li:last-child { border-bottom: none; }
        @media (max-width: 600px) {
            .intro { flex-direction: column-reverse; gap: 1.5rem; padding: 2rem 0 1.5rem; }
            .headshot { width: 140px; height: 140px; }
            .hero-name { font-size: 1.75rem; }
        }'''

    return page('Dennis F. Gardner Jr., Ph.D.', css, NAV, body, FOOTER)

# ---------------------------------------------------------------------------
# render_about
# ---------------------------------------------------------------------------

def render_about(data):
    summary = data['summary']
    skills = data['expertise']
    jobs = data['experience']
    degrees = data['education']
    awards = data['awards']

    # Skills badges
    skill_html = '\n'.join(f'            <span class="skill-badge">{s}</span>' for s in skills)

    # Timeline
    timeline_items = []
    for j in jobs:
        bullets_html = ''.join(f'<li>{b}</li>' for b in j['bullets'])
        dept_html = f'<div class="dept">{j["dept"]}</div>' if j['dept'] else ''
        timeline_items.append(f'''            <div class="timeline-item">
                <div class="timeline-header">
                    <div>
                        <h3>{j["title"]}</h3>
                        {dept_html}
                    </div>
                    <span class="timeline-date">{j["date"]}</span>
                </div>
                <ul>{bullets_html}</ul>
            </div>''')
    timeline_html = '\n'.join(timeline_items)

    # Education
    edu_rows = []
    for d in degrees:
        note_html = f'<div class="edu-note">{d["note"]}</div>' if d['note'] else ''
        edu_rows.append(f'''            <div class="edu-item">
                <div class="edu-date">{d["date"]}</div>
                <div class="edu-content"><strong>{d["line"]}</strong>{note_html}</div>
            </div>''')
    edu_html = '\n'.join(edu_rows)

    # Awards — two columns via CSS grid
    awards_html = '\n'.join(f'            <li>{a}</li>' for a in awards)

    body = f'''    <div class="container">
        <section>
            <h2>About</h2>
            <p>{summary}</p>
        </section>

        <section>
            <h2>Areas of Expertise</h2>
            <div class="skills-grid">
{skill_html}
            </div>
        </section>

        <section>
            <h2>Work Experience</h2>
            <div class="timeline">
{timeline_html}
            </div>
        </section>

        <section>
            <h2>Education</h2>
            <div class="edu-list">
{edu_html}
            </div>
        </section>

        <section>
            <h2>Awards, Fellowships &amp; Scholarships</h2>
            <ul class="awards-list">
{awards_html}
            </ul>
        </section>
    </div>'''

    css = '''        section { margin-bottom: 3rem; }
        .skills-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 0.5rem; }
        .skill-badge {
            background: #f0f9ff;
            border-left: 3px solid #0ea5e9;
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 0.875rem;
            color: #0c4a6e;
        }
        .timeline { display: flex; flex-direction: column; gap: 1rem; }
        .timeline-item {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            transition: box-shadow 0.2s, transform 0.2s;
        }
        .timeline-item:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }
        .timeline-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
            margin-bottom: 0.75rem;
        }
        .timeline-date {
            font-size: 0.8rem;
            color: #6b7280;
            font-style: italic;
            white-space: nowrap;
            flex-shrink: 0;
            margin-top: 0.2rem;
        }
        .timeline-item h3 { font-size: 1rem; }
        .dept { color: #6b7280; font-style: italic; font-size: 0.9rem; margin-top: 0.2rem; }
        .timeline-item ul { margin: 0; padding-left: 1.25rem; }
        .timeline-item li { margin-bottom: 0.3rem; font-size: 0.93rem; color: #374151; }
        .edu-list { display: flex; flex-direction: column; gap: 1rem; }
        .edu-item { display: grid; grid-template-columns: 130px 1fr; gap: 1rem; align-items: start; }
        .edu-date { color: #6b7280; font-style: italic; font-size: 0.875rem; text-align: right; padding-top: 2px; }
        .edu-note { font-style: italic; color: #6b7280; font-size: 0.875rem; margin-top: 0.25rem; }
        .awards-list {
            list-style: none;
            padding: 0;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px 16px;
        }
        .awards-list li {
            padding: 6px 10px;
            background: #f0f9ff;
            border-left: 3px solid #0ea5e9;
            border-radius: 4px;
            font-size: 0.875rem;
            color: #0c4a6e;
        }
        @media (max-width: 700px) {
            .timeline-header { flex-direction: column; gap: 0.25rem; }
            .edu-item { grid-template-columns: 1fr; }
            .edu-date { text-align: left; }
            .awards-list { grid-template-columns: 1fr; }
        }'''

    return page('About – Dennis F. Gardner Jr.', css, NAV, body, FOOTER)

# ---------------------------------------------------------------------------
# render_contact
# ---------------------------------------------------------------------------

def render_contact(data):
    contact = data['contact']
    email = contact.get('email', 'dennisfgardner@gmail.com')
    phone = contact.get('phone', '970-412-4875')
    city = contact.get('city', 'Vienna, VA')
    scholar_url = contact.get('scholar_url', 'https://scholar.google.com/citations?user=uYXouIIAAAAJ')

    body = f'''    <div class="container">
        <section>
            <h2>Get in Touch</h2>
            <p>I'm open to new opportunities in systems engineering, AI/ML research, scientific consulting, and related fields. Feel free to reach out.</p>
        </section>
        <div class="contact-grid">
            <div class="contact-item">
                <h3>Email</h3>
                <p><a href="mailto:{email}">{email}</a></p>
            </div>
            <div class="contact-item">
                <h3>Phone</h3>
                <p>{phone}</p>
            </div>
            <div class="contact-item">
                <h3>Location</h3>
                <p>{city}</p>
            </div>
            <div class="contact-item">
                <h3>Publications &amp; Patents</h3>
                <p><a href="{scholar_url}" target="_blank" rel="noopener">Google Scholar Profile</a></p>
            </div>
        </div>
    </div>'''

    css = '''        section { margin-bottom: 2rem; }
        .contact-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }
        .contact-item {
            background: #f0f9ff;
            border: 1px solid #e0f2fe;
            border-left: 4px solid #0ea5e9;
            padding: 1.25rem 1.5rem;
            border-radius: 8px;
        }
        .contact-item h3 { margin: 0 0 0.5rem; color: #0c4a6e; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.07em; }
        .contact-item p { margin: 0; font-size: 0.95rem; }
        @media (max-width: 600px) { .contact-grid { grid-template-columns: 1fr; } }'''

    return page('Contact – Dennis F. Gardner Jr.', css, NAV, body, FOOTER)

# ---------------------------------------------------------------------------
# render_publications
# ---------------------------------------------------------------------------

def render_publications(data):
    pubs = data['publications']
    other_pubs = data['other_publications']
    patents = data['patents']

    def pub_li(i, entry):
        notes = ''.join(
            f'<div class="pub-note">&#8594; {n}</div>'
            for n in entry['notes'])
        return f'<li value="{i+1}"><div class="pub-text">{entry["text"]}</div>{notes}</li>'

    pubs_html = '\n'.join(pub_li(i, e) for i, e in enumerate(pubs))
    other_html = '\n'.join(pub_li(i, e) for i, e in enumerate(other_pubs))
    patents_html = '\n'.join(
        f'<li value="{i+1}">{e["text"]}</li>'
        for i, e in enumerate(patents))

    body = f'''    <div class="container">
        <div class="pub-stats">
            19 peer-reviewed publications &nbsp;·&nbsp; 1,900+ citations &nbsp;·&nbsp; h-index 18 &nbsp;·&nbsp; 5 patents
        </div>

        <section>
            <h2>Peer-Reviewed Publications</h2>
            <ol class="pub-list">
{pubs_html}
            </ol>
        </section>

        <section>
            <h2>Patents</h2>
            <ol class="pub-list">
{patents_html}
            </ol>
        </section>

        <section>
            <h2>Other Publications</h2>
            <ol class="pub-list">
{other_html}
            </ol>
        </section>
    </div>'''

    css = '''        section { margin-bottom: 3rem; }
        .pub-stats {
            background: #f0f9ff;
            color: #0c4a6e;
            border: 1px solid #bae6fd;
            text-align: center;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            font-size: 0.95rem;
            font-weight: 500;
        }
        .pub-list { padding-left: 1.75rem; }
        .pub-list li {
            margin-bottom: 1.125rem;
            padding-bottom: 1.125rem;
            border-bottom: 1px solid #e5e7eb;
            font-size: 0.93rem;
            line-height: 1.6;
        }
        .pub-list li:last-child { border-bottom: none; }
        .pub-note {
            color: #0ea5e9;
            font-style: italic;
            font-size: 0.875rem;
            margin-top: 4px;
        }'''

    return page('Publications – Dennis F. Gardner Jr.', css, NAV, body, FOOTER)

# ---------------------------------------------------------------------------
# Headshot
# ---------------------------------------------------------------------------

def generate_headshot():
    """Regenerate the web-sized headshot from HEADSHOT_SRC using macOS `sips`.

    Skips gracefully (with a note) if the source photo or `sips` is missing, so
    the page generation itself never fails on account of the image.
    """
    if not os.path.exists(HEADSHOT_SRC):
        print(f"Note: {HEADSHOT_SRC} not found — skipping headshot resize "
              f"(index.html still expects {HEADSHOT_WEB}).")
        return
    if shutil.which("sips") is None:
        print("Note: `sips` not available (macOS only) — skipping headshot resize. "
              f"Resize {HEADSHOT_SRC} to {HEADSHOT_MAX_PX}px manually and save as {HEADSHOT_WEB}.")
        return

    result = subprocess.run(
        ["sips", "-Z", str(HEADSHOT_MAX_PX), HEADSHOT_SRC, "--out", HEADSHOT_WEB],
        capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Wrote {HEADSHOT_WEB} (resized from {HEADSHOT_SRC}, max {HEADSHOT_MAX_PX}px)")
    else:
        print(f"Warning: sips failed to resize {HEADSHOT_SRC}: {result.stderr.strip()}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        with open(CV_PATH, encoding='utf-8') as f:
            tex = f.read()
    except FileNotFoundError:
        print(f"Error: {CV_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    sections = split_sections(tex)

    data = {
        'contact':           parse_header(sections['__header__']),
        'summary':           parse_summary(sections.get('Professional Summary', '')),
        'expertise':         parse_expertise(sections.get('Areas of Expertise', '')),
        'experience':        parse_work_experience(sections.get('Work Experience', '')),
        'awards':            parse_awards(sections.get('Awards, Fellowships \\& Scholarships', '')
                                          or sections.get('Awards, Fellowships & Scholarships', '')),
        'education':         parse_education(sections.get('Education', '')),
        'patents':           parse_enumerate(sections.get('Patents', '')),
        'publications':      parse_enumerate(
                                 sections.get('Publications -- 19 peer-reviewed, 1,900+ citations, h-index 18', ''),
                                 pub_mode=True),
        'other_publications': parse_enumerate(sections.get('Other Publications', ''), pub_mode=True),
    }

    files = {
        'index.html':        render_index(data),
        'about.html':        render_about(data),
        'contact.html':      render_contact(data),
        'publications.html': render_publications(data),
    }

    for fname, html in files.items():
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Wrote {fname}")

    generate_headshot()

    # Sanity checks
    exp_count = len(data['experience'])
    pub_count = len(data['publications'])
    print(f"\nParsed: {exp_count} work entries, {pub_count} publications, "
          f"{len(data['patents'])} patents, {len(data['expertise'])} skills, "
          f"{len(data['awards'])} awards")

if __name__ == '__main__':
    main()
