#!/usr/bin/env python3
"""Build the photo side of clicksbyg.com from photos/site.json.

    python3 tools/publish.py

Makes metadata-free web copies in img/ of each export in photos/source/
(only when the export is newer), then regenerates the home, collection,
photo, about and licensing pages and assets/photos.css. The app pages
(/apps/, /philatally/, /stampalbum-pro/) are hand-written and never touched.
"""
import json
import shutil
import sys
from html import escape as e
from pathlib import Path

from images import encode, outputs, picture
from render import collection_cards, enquire_href, fill, grid, page

ROOT = Path(__file__).resolve().parent.parent


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def load():
    data = json.loads((ROOT / "photos" / "site.json").read_text())
    for p in data["photos"]:
        src = ROOT / "photos" / "source" / p["file"]
        if not src.exists():
            sys.exit(f"missing source image: {src}")
        encode(p, src, ROOT / "img")
    data["by_slug"] = {p["slug"]: p for p in data["photos"]}
    data["by_coll"] = {c["slug"]: [p for p in data["photos"] if p["collection"] == c["slug"]]
                       for c in data["collections"]}
    data["collections"] = visible_collections(data)
    return data


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
        f".p-{p['slug']}{{--ar:{p['ar']};--ph:{p['bg']}}}\n" for p in d["photos"]))


def build_home(d):
    site, photos = d["site"], d["photos"]
    hero = next((p for p in photos if p.get("featured")), photos[0])
    body = fill("home.html", slug=hero["slug"], hero_title=e(hero["title"]),
                hero_picture=picture(hero, "100vw", cls="hero-img", loading="eager", priority=True),
                tagline=e(site["tagline"]), name=e(site["name"]), grid=grid(photos[:12]),
                cards=collection_cards(d["collections"], d["by_slug"], d["by_coll"]))
    write(ROOT / "index.html", page(site, f"{e(site['name'])} — photography", site["tagline"],
                                    body, og_image=f"/img/{hero['slug']}-1280.jpg", body_class="home"))


def build_collections(d):
    site, name = d["site"], e(d["site"]["name"])
    cards = collection_cards(d["collections"], d["by_slug"], d["by_coll"])
    write(ROOT / "collections" / "index.html", page(
        site, f"Collections — {name}", "Photograph collections by Clicks by G.",
        f'<section class="band top"><h1>Collections</h1>{cards}</section>',
        current="/collections/", url="/collections/"))
    for c in d["collections"]:
        body = (f'<section class="band top"><p class="crumb"><a href="/collections/">Collections</a></p>'
                f'<h1>{e(c["title"])}</h1><p class="lede">{e(c.get("blurb", ""))}</p>'
                f'{grid(d["by_coll"][c["slug"]])}</section>')
        write(ROOT / "collections" / c["slug"] / "index.html", page(
            site, f"{e(c['title'])} — {name}", c.get("blurb", ""), body, current="/collections/",
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
    body = fill(
        "photo.html", slug=p["slug"], title=e(p["title"]), exif=exif,
        picture=picture(p, "100vw", cls="photo-img", loading="eager", priority=True),
        collection=p["collection"], collection_title=e(coll_titles[p["collection"]]),
        caption=f"<p>{e(p['caption'])}</p>" if p.get("caption") else "",
        print_href=e(p.get("print_url") or enquire_href(site, f"Print: {p['title']}")),
        license_href=e(p.get("license_url") or enquire_href(site, f"Licence: {p['title']}")),
        pager=pager(d["by_coll"][p["collection"]], p))
    write(ROOT / "photo" / p["slug"] / "index.html", page(
        site, f"{e(p['title'])} — {e(site['name'])}", p.get("alt") or p["title"], body,
        og_image=f"/img/{p['slug']}-1280.jpg", body_class="photo-page", url=f"/photo/{p['slug']}/"))


def build_about(site):
    paras = "".join(f"<p>{e(t)}</p>" for t in site.get("about", []))
    body = (f'<section class="band top prose-g"><h1>About</h1>{paras}'
            f'<p><a class="g-btn" href="/licensing/">Prints &amp; licensing</a></p></section>')
    write(ROOT / "about" / "index.html", page(
        site, f"About — {e(site['name'])}", "About the photographer behind Clicks by G.",
        body, current="/about/", url="/about/"))


def build_licensing(site):
    email = site.get("contact_email")
    contact = (f'<p>Email <a href="mailto:{e(email)}">{e(email)}</a> with the photograph\'s title, '
               f'the size or use you have in mind, and where you are.</p>' if email else
               '<p class="todo">Contact email not set yet: add <code>contact_email</code> to '
               '<code>photos/site.json</code>.</p>')
    write(ROOT / "licensing" / "index.html", page(
        site, f"Prints &amp; licensing — {e(site['name'])}",
        "Buy fine-art prints or license photographs by Clicks by G.",
        fill("licensing.html", contact=contact), current="/licensing/", url="/licensing/"))


def build():
    d = load()
    # These folders are entirely generated; clearing them drops pages for
    # photos or collections that were renamed or removed.
    for generated in ("collections", "photo"):
        shutil.rmtree(ROOT / generated, ignore_errors=True)
    prune_images(d["photos"])
    if not d["site"].get("contact_email"):
        print("warning: site.contact_email is empty in photos/site.json; "
              "enquiry buttons point at /licensing/ until you set it")
    build_css(d)
    build_home(d)
    build_collections(d)
    titles = {c["slug"]: c["title"] for c in d["collections"]}
    for p in d["photos"]:
        build_photo(d, p, titles)
    build_about(d["site"])
    build_licensing(d["site"])
    print(f"built {len(d['photos'])} photos in {len(d['collections'])} collections")


if __name__ == "__main__":
    build()
