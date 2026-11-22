"""Fill the HTML templates in tools/templates/ and build shared fragments."""
import json
from datetime import date
from html import escape as e
from pathlib import Path
from string import Template
from urllib.parse import quote

from images import picture

TEMPLATES = Path(__file__).resolve().parent / "templates"
NAV = (("/collections/", "Collections"), ("/about/", "About"),
       ("/licensing/", "Prints &amp; licensing"), ("/contact/", "Contact"), ("/apps/", "Apps"))
# GitHub Pages can't send headers, so the policy rides in a meta tag.
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
       "object-src 'none'; base-uri 'self'; form-action 'self'")


def fill(template, **values):
    return Template((TEMPLATES / template).read_text()).substitute(values)


def page(site, title, desc, body, current="", og_image=None, body_class="", url="/", head=""):
    """url=None leaves out the canonical link, for pages that shouldn't be indexed."""
    cur = ' aria-current="page"'
    links = "".join(f'<a href="{h}"{cur if h == current else ""}>{t}</a>' for h, t in NAV)
    og = f'<meta property="og:image" content="https://clicksbyg.com{og_image}">' if og_image else ""
    insta = (f'<a href="https://instagram.com/{e(site["instagram"])}">Instagram</a>'
             if site.get("instagram") else "")
    canonical = f'<link rel="canonical" href="https://clicksbyg.com{url}">' if url else ""
    return fill("base.html", csp=CSP, title=title, desc=e(desc), canonical=canonical, og=og,
                body_class=body_class, name=e(site["name"]), links=links, body=body,
                span=_years(site["copyright_start"]), insta=insta, head=head)


def _years(start):
    year = date.today().year
    return f"{start}–{year}" if year > start else str(year)


def grid(photos):
    return '<div class="jg">' + "".join(
        f'<a class="jg-item p-{p["slug"]}" href="/photo/{p["slug"]}/">'
        f'<i aria-hidden="true"></i>{picture(p, "(max-width: 700px) 50vw, 33vw")}'
        f'<span class="jg-cap">{e(p["title"])}</span></a>'
        for p in photos) + "</div>"


def collection_cards(collections, by_slug, by_coll):
    return '<div class="c-grid">' + "".join(
        _card(c, by_slug[c["cover"]], len(by_coll[c["slug"]])) for c in collections) + "</div>"


def _card(c, cover, n):
    return (f'<a class="c-card p-{cover["slug"]}" href="/collections/{c["slug"]}/">'
            f'{picture(cover, "(max-width: 700px) 100vw, 33vw", cls="c-img")}'
            f'<span class="c-text"><span class="c-title">{e(c["title"])}</span>'
            f'<span class="c-meta">{n} photograph{"s" if n != 1 else ""}</span></span></a>')


# Pre-filled emails ask for exactly what a quote needs, so one reply will do.
LICENSE_FORM = """Photo: {photo}

What will it be used for? (website, social media, book or magazine, advertising, product)
Where will it appear?
Size or resolution needed:
For how long? (e.g. 1 year, 5 years, perpetual)
Region (e.g. India, worldwide):
Your name and organisation:
Budget, if you have one:
"""
PRINT_FORM = """Photo: {photo}

Size (e.g. A4, A3, 24 x 16 in):
Finish: matte or lustre paper, framed or unframed:
Delivery city and country:
"""


def licensable(site, p):
    """schema.org data that earns the "Licensable" badge in Google Images.
    It's data, not script, so the CSP doesn't block it."""
    data = {
        "@context": "https://schema.org", "@type": "ImageObject",
        "contentUrl": f"https://clicksbyg.com/img/{p['slug']}-2048.jpg",
        "name": p["title"], "creditText": site["name"],
        "creator": {"@type": "Person", "name": site["name"]},
        "copyrightNotice": f"© {site['copyright_start']} {site['name']}",
        "license": "https://clicksbyg.com/licensing/",
        "acquireLicensePage": "https://clicksbyg.com/contact/",
    }
    # "</" could close the script element early; JSON allows "<\/" instead.
    text = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{text}</script>'


def enquire_href(site, subject, form="", photo="(title or link)"):
    if not site.get("contact_email"):
        return "/contact/"
    body = f"&body={quote(form.format(photo=photo))}" if form else ""
    return f"mailto:{site['contact_email']}?subject={quote(subject)}{body}"
