"""The pages rendered from the CV, plus the thesis page.

Each render_* takes the parsed CV data (see latex.parse_cv) and returns a
complete HTML document. They emit only markup and class names -- never CSS.
"""

from .layout import page, page_title, site


def stats_line(data):
    """The publication/patent headline, assembled once and used on two pages.

    The counts are counted, not typed: they come from the parsed CV, so they
    cannot drift out of step with the actual list the way two hand-written
    copies of this sentence did.
    """
    s = site()['stats']
    return {
        'publications': len(data['publications']),
        'citations': s['citations'],
        'h_index': s['h_index'],
        'patents': len(data['patents']),
    }


# ---------------------------------------------------------------------------
# index.html
# ---------------------------------------------------------------------------

def render_index(data):
    summary = data['summary']
    first_two = '. '.join(summary.split('. ')[:2]) + '.'
    st = stats_line(data)

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
                <li><a href="publications.html">Publications &amp; Patents</a> — {st['publications']} peer-reviewed papers, {st['citations']} citations, h-index {st['h_index']}, and {st['patents']} patents</li>
                <li><a href="thesis.html">Ph.D. Thesis</a> — full dissertation, view or download</li>
                <li><a href="contact.html">Contact</a> — get in touch</li>
            </ul>
        </div>
    </div>'''

    return page(page_title(), 'home', body)


# ---------------------------------------------------------------------------
# about.html
# ---------------------------------------------------------------------------

def render_about(data):
    skill_html = '\n'.join(
        f'            <span class="skill-badge">{s}</span>' for s in data['expertise'])

    timeline_items = []
    for j in data['experience']:
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

    edu_rows = []
    for d in data['education']:
        note_html = f'<div class="edu-note">{d["note"]}</div>' if d['note'] else ''
        edu_rows.append(f'''            <div class="edu-item">
                <div class="edu-date">{d["date"]}</div>
                <div class="edu-content"><strong>{d["line"]}</strong>{note_html}</div>
            </div>''')
    edu_html = '\n'.join(edu_rows)

    # Awards — two columns via CSS grid
    awards_html = '\n'.join(f'            <li>{a}</li>' for a in data['awards'])

    body = f'''    <div class="container">
        <section>
            <h2>About</h2>
            <p>{data['summary']}</p>
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

    return page(page_title('About'), 'about', body)


# ---------------------------------------------------------------------------
# contact.html
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

    return page(page_title('Contact'), 'contact', body)


# ---------------------------------------------------------------------------
# publications.html
# ---------------------------------------------------------------------------

def render_publications(data):
    st = stats_line(data)

    def pub_li(i, entry):
        notes = ''.join(
            f'<div class="pub-note">&#8594; {n}</div>'
            for n in entry['notes'])
        return f'<li value="{i+1}"><div class="pub-text">{entry["text"]}</div>{notes}</li>'

    pubs_html = '\n'.join(pub_li(i, e) for i, e in enumerate(data['publications']))
    other_html = '\n'.join(pub_li(i, e) for i, e in enumerate(data['other_publications']))
    patents_html = '\n'.join(
        f'<li value="{i+1}">{e["text"]}</li>'
        for i, e in enumerate(data['patents']))

    body = f'''    <div class="container">
        <div class="pub-stats">
            {st['publications']} peer-reviewed publications &nbsp;·&nbsp; {st['citations']} citations &nbsp;·&nbsp; h-index {st['h_index']} &nbsp;·&nbsp; {st['patents']} patents
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

    return page(page_title('Publications'), 'publications', body)


# ---------------------------------------------------------------------------
# thesis.html
# ---------------------------------------------------------------------------

def render_thesis():
    """The thesis page: title/degree block, abstract, embedded PDF viewer.

    The PDF is presented directly rather than converted to HTML. Content comes
    from the `thesis` block in content/site.yaml (the CV has no thesis section).
    """
    info = site()['thesis']
    pdf = info['pdf']
    note_html = f'<p class="thesis-note">{info["note"]}</p>' if info.get('note') else ''
    if info.get('abstract'):
        abstract_html = f'<p class="thesis-abstract">{info["abstract"]}</p>'
    else:
        abstract_html = '<p class="thesis-abstract thesis-abstract-placeholder">Abstract coming soon.</p>'

    body = f'''    <div class="container container-wide">
        <section class="thesis-header">
            <h2>{info["title"]}</h2>
            <p class="thesis-meta">{info["degree"]} &middot; {info["institution"]} &middot; {info["date"]}</p>
            {note_html}
            {abstract_html}
            <div class="cta-buttons">
                <a class="cta-btn cta-btn-primary" href="{pdf}" download>Download PDF</a>
            </div>
        </section>

        <section>
            <iframe class="thesis-viewer" src="{pdf}" title="{info['title']}">
                <p>Your browser doesn't support embedded PDFs.
                    <a href="{pdf}">Download the thesis PDF</a> instead.</p>
            </iframe>
            <div class="thesis-viewer-fallback">
                <p>PDF preview isn't supported in this browser. Open the full document instead:</p>
                <a class="cta-btn cta-btn-primary" href="{pdf}" target="_blank" rel="noopener">Open PDF</a>
            </div>
        </section>
    </div>'''

    return page(page_title('Thesis'), 'thesis', body)
