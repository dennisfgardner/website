#!/usr/bin/env python3
"""Parse CV_ver18_20260706.tex and generate website HTML pages."""

import os
import re
import shutil
import subprocess
import sys

import blog_posts

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

# All site styling lives in styles.css (the single source of truth). The pages
# link it rather than carrying inline CSS — see styles.css to change any style.
STYLESHEET = "styles.css"

# The nav links, in order. Each is (href, label, active_key); the active page's
# link gets class="active" so it highlights site-wide.
NAV_LINKS = [
    ('index.html', 'Home', 'home'),
    ('about.html', 'About', 'about'),
    ('publications.html', 'Publications', 'publications'),
    ('blog.html', 'Blog', 'blog'),
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
        <a href="index.html" class="nav-brand">Dennis F. Gardner Jr., Ph.D.</a>
        <div class="nav-links">
{links}
        </div>
    </nav>'''

FOOTER = '''    <footer>
        <p>&copy; 2025 Dennis F. Gardner Jr., Ph.D.</p>
    </footer>'''

def page(title, active, body):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{STYLESHEET}">
</head>
<body>
{nav(active)}
{body}
{FOOTER}
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
                <p class="tagline">Physicist &nbsp;·&nbsp; Systems Engineer &nbsp;·&nbsp; AI &amp; ML Practitioner</p>
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

    return page('Dennis F. Gardner Jr., Ph.D.', 'home', body)

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

    return page('About – Dennis F. Gardner Jr.', 'about', body)

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

    return page('Contact – Dennis F. Gardner Jr.', 'contact', body)

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

    return page('Publications – Dennis F. Gardner Jr.', 'publications', body)

# ---------------------------------------------------------------------------
# render_blog
# ---------------------------------------------------------------------------

def render_blog(posts):
    articles = []
    for post in posts:
        tags_html = '\n'.join(
            f'                <span class="tag">{t}</span>' for t in post['tags'])

        comments = post.get('comments', [])
        comment_items = '\n'.join(
            f'''                <div class="comment">
                    <p><span class="comment-author">{c["author"]}</span><span class="comment-date">{c["date"]}</span></p>
                    <p>{c["text"]}</p>
                </div>''' for c in comments)
        comments_html = f'''
            <div class="comments-section">
                <h3>Comments ({len(comments)})</h3>
{comment_items}
            </div>''' if comments else ''

        articles.append(f'''        <article id="{post['id']}" class="blog-post">
            <div class="blog-header">
                <h2>{post['title']}</h2>
                <span class="blog-date">{post['date']}</span>
            </div>

            <div class="blog-content">
{post['content']}
            </div>

            <div class="tags">
{tags_html}
            </div>
{comments_html}
        </article>''')

    articles_html = '\n\n'.join(articles)

    body = f'''    <div class="container">
        <h2>Blog</h2>
        <p class="blog-intro">Thoughts on physics, AI, and systems engineering.</p>

{articles_html}
    </div>'''

    return page('Blog – Dennis F. Gardner Jr.', 'blog', body)

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
        'blog.html':         render_blog(blog_posts.POSTS),
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
