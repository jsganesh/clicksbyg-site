#!/usr/bin/env python3
"""Build the photo side of clicksbyg.com from photos/site.json.

    python3 tools/publish.py

Makes metadata-free web copies in img/ of each export in photos/source/
(only when the export is newer), then regenerates the home, collection,
photo, about, licensing and contact pages, assets/photos.css,
sitemap.xml and robots.txt. The app pages
(/apps/, /philatally/, /stampalbum-pro/) are hand-written and never touched.
"""
import json
import re
import shutil
import sys
from html import escape as e
from pathlib import Path

import seo
import sitemap
from images import credit_exif, encode, outputs, picture
from render import (LICENSE_FORM, PRINT_FORM, collection_cards, enquire_href, fill, grid,
                    licensable, page)

ROOT = Path(__file__).resolve().parent.parent
FOCUS = re.compile(r"(100|\d{1,2})% (100|\d{1,2})%")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def load():
    data = json.loads((ROOT / "photos" / "site.json").read_text())
    exif = credit_exif(data["site"]["name"], copyright_notice(data["site"]))
    for p in data["photos"]:
        src = ROOT / "photos" / "source" / p["file"]
        if not src.exists():
            sys.exit(f"missing source image: {src}")
        # focus is written into CSS, so only "x% y%" gets through.
        if not FOCUS.fullmatch(p.setdefault("focus", "50% 50%")):
            sys.exit(f"{p['slug']}: focus must look like \"60% 40%\", got {p['focus']!r}")
        encode(p, src, ROOT / "img", exif)
    data["by_slug"] = {p["slug"]: p for p in data["photos"]}
    data["by_coll"] = {c["slug"]: [p for p in data["photos"] if p["collection"] == c["slug"]]
                       for c in data["collections"]}
    data["collections"] = visible_collections(data)
    data["shared"] = seo.shared_subjects(data["photos"])
    return data


def copyright_notice(site):
    # ASCII only: EXIF text fields are ASCII, so no "©".
    return (f"Copyright {site['copyright_start']} {site['name']}. All rights reserved. "
            "Licensing: https://clicksbyg.com/licensing/")


def visible_collections(data):
    """Collections with photos, each with a valid cover. Empty ones stay
    hidden, so a new category can be listed before its photos are ready."""
    shown = []
    for c in data["collections"]:
        members = data["by_coll"][c["slug"]]
        if not members:
            print(f"note: collection '{c['slug']}' has no photos yet and is hidden")
            continue
        if c.get("cover") not in {p["slug"] for p in members}:
            c["cover"] = members[0]["slug"]
        shown.append(c)
    return shown


def prune_images(photos):
    keep = {o for p in photos for o in outputs(p["slug"], ROOT / "img")}
    for f in (ROOT / "img").glob("*"):
        if f not in keep:
            f.unlink()
            print("removed", f.name)


def build_css(d):
    # Per-photo values live in a stylesheet so the CSP can forbid inline styles.
    write(ROOT / "assets" / "photos.css", "".join(
        f".p-{p['slug']}{{--ar:{p['ar']};--ph:{p['bg']};--focus:{p['focus']}}}\n"
        for p in d["photos"]))


def build_home(d):
    site, photos = d["site"], d["photos"]
    hero = next((p for p in photos if p.get("featured")), photos[0])
    body = fill("home.html", slug=hero["slug"], hero_title=e(hero["title"]),
                hero_picture=picture(hero, "100vw", cls="hero-img", loading="eager", priority=True),
                tagline=e(site["tagline"]), name=e(site["name"]), grid=grid(photos[:12]),
                cards=collection_cards(d["collections"], d["by_slug"], d["by_coll"]))
    write(ROOT / "index.html", page(site, e(f"{site['home_title']} | {site['name']}"),
                                    site["description"], body,
                                    og_image=f"/img/{hero['slug']}-1280.jpg", body_class="home"))


def build_collections(d):
    site = d["site"]
    cards = collection_cards(d["collections"], d["by_slug"], d["by_coll"])
    write(ROOT / "collections" / "index.html", page(
        site, e(f"Photography Collections from {site['region']} | {site['name']}"),
        seo.clip(f"Browse photographs from {site['region']} by {site['name']}: "
                 + ", ".join(c["title"].lower() for c in d["collections"]) + f". {seo.OFFER}"),
        f'<section class="band top"><h1>Collections</h1>{cards}</section>',
        current="/collections/", url="/collections/"))
    for c in d["collections"]:
        body = (f'<section class="band top"><p class="crumb"><a href="/collections/">Collections</a></p>'
                f'<h1>{e(c["title"])}</h1><p class="lede">{e(c.get("blurb", ""))}</p>'
                f'{grid(d["by_coll"][c["slug"]])}</section>')
        write(ROOT / "collections" / c["slug"] / "index.html", page(
            site, e(seo.collection_title(site, c)),
            seo.collection_desc(site, c, len(d["by_coll"][c["slug"]])), body, current="/collections/",
            og_image=f"/img/{c['cover']}-1280.jpg", url=f"/collections/{c['slug']}/"))


def pager(seq, p):
    i = seq.index(p)
    prev_p = seq[i - 1] if i > 0 else None
    next_p = seq[i + 1] if i < len(seq) - 1 else None
    left = f'<a rel="prev" href="/photo/{prev_p["slug"]}/">← {e(prev_p["title"])}</a>' if prev_p else "<span></span>"
    right = f'<a rel="next" href="/photo/{next_p["slug"]}/">{e(next_p["title"])} →</a>' if next_p else "<span></span>"
    return left + right


def build_photo(d, p, coll_titles):
    site = d["site"]
    fields = (("Species", "species"), ("Place", "place"), ("Date", "date"), ("Camera", "camera"),
              ("Lens", "lens"), ("Settings", "settings"))
    exif = "".join(f"<dt>{k}</dt><dd>{e(p[f])}</dd>" for k, f in fields if p.get(f))
    ref = f"{p['title']} (https://clicksbyg.com/photo/{p['slug']}/)"
    body = fill(
        "photo.html", slug=p["slug"], title=e(p["title"]), exif=exif,
        picture=picture(p, "100vw", cls="photo-img", loading="eager", priority=True),
        collection=p["collection"], collection_title=e(coll_titles[p["collection"]]),
        caption=f"<p>{e(p['caption'])}</p>" if p.get("caption") else "",
        print_href=e(p.get("print_url") or enquire_href(site, f"Print: {p['title']}", PRINT_FORM, ref)),
        license_href=e(p.get("license_url") or enquire_href(site, f"Licence: {p['title']}", LICENSE_FORM, ref)),
        pager=pager(d["by_coll"][p["collection"]], p))
    write(ROOT / "photo" / p["slug"] / "index.html", page(
        site, e(seo.photo_title(site, p, d["shared"])), seo.photo_desc(p), body,
        og_image=f"/img/{p['slug']}-1280.jpg", body_class="photo-page", url=f"/photo/{p['slug']}/",
        head=licensable(site, p)))


def build_about(site):
    paras = "".join(f"<p>{e(t)}</p>" for t in site.get("about", []))
    body = (f'<section class="band top prose-g"><h1>About</h1>{paras}'
            f'<p><a class="g-btn" href="/licensing/">Prints &amp; licensing</a></p></section>')
    write(ROOT / "about" / "index.html", page(
        site, e(f"About {site['name']}, Photographer in {site['region']}"),
        seo.clip(" ".join(site.get("about", [])[:1]) or site["description"]),
        body, current="/about/", url="/about/"))


def build_licensing(site):
    write(ROOT / "licensing" / "index.html", page(
        site, e(f"Buy Photo Prints & License Images | {site['name']}"),
        f"Order fine-art prints or license bird and wildlife photographs by {site['name']}: "
        "editorial, commercial and personal use.",
        fill("licensing.html"), current="/licensing/", url="/licensing/"))


def build_contact(site):
    email = site.get("contact_email") or sys.exit("photos/site.json: set site.contact_email")
    body = fill("contact.html", email=e(email),
                license_href=e(enquire_href(site, "Licence request", LICENSE_FORM)),
                print_href=e(enquire_href(site, "Print enquiry", PRINT_FORM)),
                report_href=e(enquire_href(site, "Unlicensed use of my photo")))
    write(ROOT / "contact" / "index.html", page(
        site, e(f"Contact {site['name']} | Prints, Licensing & Commissions"),
        f"Request a photo licence, order a print or ask about commissions with {site['name']}.",
        body, current="/contact/", url="/contact/"))


def build_404(d):
    # GitHub Pages serves /404.html for any missing path, so every link is absolute.
    body = ('<section class="band top prose-g"><h1>That page has flown off</h1>'
            "<p>The link may be old or mistyped. The photographs are still here.</p>"
            '<p><a class="g-btn" href="/">Back to the gallery</a> '
            '<a class="g-btn ghost" href="/collections/">See the collections</a></p>'
            f'{grid(d["photos"][:6])}</section>')
    write(ROOT / "404.html", page(d["site"], e(f"Page not found | {d['site']['name']}"),
                                  "This page doesn't exist.", body, url=None,
                                  head='<meta name="robots" content="noindex">'))


def build():
    d = load()
    # These folders are entirely generated; clearing them drops pages for
    # photos or collections that were renamed or removed.
    for generated in ("collections", "photo"):
        shutil.rmtree(ROOT / generated, ignore_errors=True)
    prune_images(d["photos"])
    build_css(d)
    build_home(d)
    build_collections(d)
    titles = {c["slug"]: c["title"] for c in d["collections"]}
    for p in d["photos"]:
        build_photo(d, p, titles)
    build_about(d["site"])
    build_licensing(d["site"])
    build_contact(d["site"])
    build_404(d)
    sitemap.build(ROOT, d["photos"])
    print(f"built {len(d['photos'])} photos in {len(d['collections'])} collections")


if __name__ == "__main__":
    build()
