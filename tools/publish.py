#!/usr/bin/env python3
"""Build the photo side of clicksbyg.com from photos/site.json.

    python3 tools/publish.py

For every photo listed in photos/site.json it:
  * reads the export from photos/source/<file> (that folder is not committed),
  * writes web copies to img/ at 640, 1280 and 2048 px wide, as WebP and JPEG,
    with all metadata (GPS, camera serial, etc.) stripped,
  * then regenerates the home page, collection pages, photo pages, about and
    licensing pages, and assets/photos.css.

Images are only re-encoded when the source is newer than the web copy.
The app pages (/philatally/, /stampalbum-pro/, /apps/) are hand-written and
never touched by this script.
"""
import html
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "photos" / "source"
IMG = ROOT / "img"
WIDTHS = (640, 1280, 2048)
e = html.escape


# ---------------------------------------------------------------- images

def process(photo):
    src = SRC / photo["file"]
    if not src.exists():
        sys.exit(f"missing source image: {src}")
    slug = photo["slug"]
    outs = [IMG / f"{slug}-{w}.{ext}" for w in WIDTHS for ext in ("webp", "jpg")]
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)  # honour camera rotation, then drop EXIF
        im = im.convert("RGB")
        w, h = im.size
        avg = im.resize((1, 1), Image.LANCZOS).getpixel((0, 0))
        stale = any(not o.exists() or o.stat().st_mtime < src.stat().st_mtime for o in outs)
        if stale:
            IMG.mkdir(exist_ok=True)
            for tw in WIDTHS:
                th = round(h * min(tw, w) / w)
                r = im.resize((min(tw, w), th), Image.LANCZOS) if tw < w else im
                # No exif= argument: Pillow writes the pixels only.
                r.save(IMG / f"{slug}-{tw}.webp", "WEBP", quality=80, method=6)
                r.save(IMG / f"{slug}-{tw}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
            print("encoded", slug)
    photo["w"], photo["h"] = w, h
    photo["ar"] = round(w / h, 4)
    photo["bg"] = "#%02x%02x%02x" % avg


def picture(p, sizes, cls="", loading="lazy", priority=False):
    def srcset(ext):
        return ", ".join(f"/img/{p['slug']}-{w}.{ext} {min(w, p['w'])}w" for w in WIDTHS)
    fetch = ' fetchpriority="high"' if priority else ""
    return (
        f'<picture class="{cls}">'
        f'<source type="image/webp" srcset="{srcset("webp")}" sizes="{sizes}">'
        f'<img src="/img/{p["slug"]}-1280.jpg" srcset="{srcset("jpg")}" sizes="{sizes}" '
        f'width="{p["w"]}" height="{p["h"]}" alt="{e(p.get("alt") or p["title"])}" '
        f'loading="{loading}" decoding="async"{fetch}>'
        f"</picture>"
    )


# ---------------------------------------------------------------- layout

CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
       "object-src 'none'; base-uri 'self'; form-action 'self'")


def page(site, title, desc, body, current="", og_image=None, body_class="", url="/"):
    nav = [("/collections/", "Collections"), ("/about/", "About"),
           ("/licensing/", "Prints &amp; licensing"), ("/apps/", "Apps")]
    cur = ' aria-current="page"'
    links = "".join(
        f'<a href="{h}"{cur if h == current else ""}>{t}</a>' for h, t in nav)
    og = f'<meta property="og:image" content="https://clicksbyg.com{og_image}">' if og_image else ""
    year = date.today().year
    span = f"{site['copyright_start']}–{year}" if year > site["copyright_start"] else str(year)
    insta = (f'<a href="https://instagram.com/{e(site["instagram"])}">Instagram</a>'
             if site.get("instagram") else "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{CSP}">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>{title}</title>
  <meta name="description" content="{e(desc)}">
  <link rel="canonical" href="https://clicksbyg.com{url}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:type" content="website">
  {og}
  <link rel="stylesheet" href="/assets/gallery.css">
  <link rel="stylesheet" href="/assets/photos.css">
  <script src="/assets/gallery.js" defer></script>
</head>
<body class="gallery {body_class}">
  <a class="skip" href="#main">Skip to content</a>
  <header class="g-header">
    <a class="g-brand" href="/">{e(site['name'])}</a>
    <nav>{links}</nav>
  </header>
  <main id="main">
{body}
  </main>
  <footer class="g-footer">
    <div class="g-footer-in">
      <p>© {span} {e(site['name'])}. All photographs are copyright and may not be
      used without a licence.</p>
      <p class="g-footer-links">
        <a href="/licensing/">Prints &amp; licensing</a>
        <a href="/about/">About</a>
        {insta}
        <span class="sep">Apps:</span>
        <a href="/philatally/">PhilaTally</a>
        <a href="/philatally/support/">Support</a>
        <a href="/philatally/privacy/">Privacy</a>
        <a href="/stampalbum-pro/">StampAlbum Pro</a>
      </p>
    </div>
  </footer>
</body>
</html>
"""


def grid(photos):
    items = "".join(
        f'<a class="jg-item p-{p["slug"]}" href="/photo/{p["slug"]}/">'
        f'<i aria-hidden="true"></i>{picture(p, "(max-width: 700px) 50vw, 33vw")}'
        f'<span class="jg-cap">{e(p["title"])}</span></a>'
        for p in photos)
    return f'<div class="jg">{items}</div>'


def collection_cards(collections, by_slug, by_coll):
    cards = []
    for c in collections:
        cover = by_slug[c["cover"]]
        n = len(by_coll[c["slug"]])
        cards.append(
            f'<a class="c-card p-{cover["slug"]}" href="/collections/{c["slug"]}/">'
            f'{picture(cover, "(max-width: 700px) 100vw, 33vw", cls="c-img")}'
            f'<span class="c-text"><span class="c-title">{e(c["title"])}</span>'
            f'<span class="c-meta">{n} photograph{"s" if n != 1 else ""}</span></span></a>')
    return f'<div class="c-grid">{"".join(cards)}</div>'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def enquire_href(site, subject):
    if site.get("contact_email"):
        return f"mailto:{site['contact_email']}?subject={quote(subject)}"
    return "/licensing/#enquire"


# ---------------------------------------------------------------- pages

def build():
    data = json.loads((ROOT / "photos" / "site.json").read_text())
    site, collections, photos = data["site"], data["collections"], data["photos"]
    if not site.get("contact_email"):
        print("warning: site.contact_email is empty in photos/site.json; "
              "enquiry buttons point at /licensing/ until you set it")
    for p in photos:
        process(p)
    by_slug = {p["slug"]: p for p in photos}
    by_coll = {c["slug"]: [p for p in photos if p["collection"] == c["slug"]] for c in collections}

    # Per-photo aspect ratio and placeholder colour live in a stylesheet,
    # so the Content-Security-Policy can forbid inline styles.
    write(ROOT / "assets" / "photos.css", "".join(
        f".p-{p['slug']}{{--ar:{p['ar']};--ph:{p['bg']}}}\n" for p in photos))

    # Home
    hero = next((p for p in photos if p.get("featured")), photos[0])
    home = f"""
    <section class="hero p-{hero['slug']}">
      {picture(hero, "100vw", cls="hero-img", loading="eager", priority=True)}
      <div class="hero-text">
        <h1>{e(site['tagline'])}</h1>
        <p><a class="g-btn" href="/collections/">See the collections</a>
        <a class="g-btn ghost" href="/licensing/">Prints &amp; licensing</a></p>
      </div>
      <a class="hero-credit" href="/photo/{hero['slug']}/">{e(hero['title'])}</a>
    </section>
    <section class="band">
      <h2 class="eyebrow">Collections</h2>
      {collection_cards(collections, by_slug, by_coll)}
    </section>
    <section class="band">
      <h2 class="eyebrow">Recent work</h2>
      {grid(photos[:12])}
    </section>
    <section class="band offer">
      <div>
        <h2>Bring one home</h2>
        <p>Every photograph is available as an archival fine-art print,
        or licensed for editorial and commercial use.</p>
      </div>
      <a class="g-btn" href="/licensing/">How it works</a>
    </section>
    <section class="band apps-strip">
      <p>Also by {e(site['name'])}: apps for stamp collectors.
      <a href="/philatally/">PhilaTally</a> for iPhone and iPad, and
      <a href="/stampalbum-pro/">StampAlbum Pro</a> for Mac.</p>
    </section>"""
    write(ROOT / "index.html", page(
        site, f"{e(site['name'])} — photography", site["tagline"], home,
        og_image=f"/img/{hero['slug']}-1280.jpg", body_class="home"))

    # Collections index and collection pages
    write(ROOT / "collections" / "index.html", page(
        site, f"Collections — {e(site['name'])}", "Photograph collections by Clicks by G.",
        f'<section class="band top"><h1>Collections</h1>'
        f'{collection_cards(collections, by_slug, by_coll)}</section>',
        current="/collections/", url="/collections/"))
    for c in collections:
        items = by_coll[c["slug"]]
        write(ROOT / "collections" / c["slug"] / "index.html", page(
            site, f"{e(c['title'])} — {e(site['name'])}", c.get("blurb", ""),
            f'<section class="band top"><p class="crumb"><a href="/collections/">Collections</a></p>'
            f'<h1>{e(c["title"])}</h1><p class="lede">{e(c.get("blurb", ""))}</p>'
            f'{grid(items)}</section>',
            current="/collections/", og_image=f"/img/{c['cover']}-1280.jpg",
            url=f"/collections/{c['slug']}/"))

    # Photo pages, with previous / next inside the collection
    titles = {c["slug"]: c["title"] for c in collections}
    for p in photos:
        seq = by_coll[p["collection"]]
        i = seq.index(p)
        prev_p, next_p = seq[i - 1] if i > 0 else None, seq[i + 1] if i < len(seq) - 1 else None
        meta = [(k, p.get(f)) for k, f in (("Place", "place"), ("Date", "date"), ("Camera", "camera"),
                                           ("Lens", "lens"), ("Settings", "settings"))]
        dl = "".join(f"<dt>{k}</dt><dd>{e(v)}</dd>" for k, v in meta if v)
        print_href = p.get("print_url") or enquire_href(site, f"Print: {p['title']}")
        lic_href = p.get("license_url") or enquire_href(site, f"Licence: {p['title']}")
        pager = "".join([
            f'<a rel="prev" href="/photo/{prev_p["slug"]}/">← {e(prev_p["title"])}</a>' if prev_p else "<span></span>",
            f'<a rel="next" href="/photo/{next_p["slug"]}/">{e(next_p["title"])} →</a>' if next_p else "<span></span>",
        ])
        caption = f"<p>{e(p['caption'])}</p>" if p.get("caption") else ""
        body = f"""
    <figure class="photo p-{p['slug']}">
      {picture(p, "100vw", cls="photo-img", loading="eager", priority=True)}
    </figure>
    <section class="photo-info">
      <div class="photo-text">
        <p class="crumb"><a href="/collections/{p['collection']}/">{e(titles[p['collection']])}</a></p>
        <h1>{e(p['title'])}</h1>
        {caption}
        <dl class="exif">{dl}</dl>
      </div>
      <div class="photo-buy">
        <a class="g-btn" href="{e(print_href)}">Buy a print</a>
        <a class="g-btn ghost" href="{e(lic_href)}">License this image</a>
        <p class="note">Archival prints in several sizes. Licences for web,
        print and commercial use. <a href="/licensing/">Details</a></p>
      </div>
    </section>
    <nav class="pager" aria-label="More in this collection">{pager}</nav>"""
        write(ROOT / "photo" / p["slug"] / "index.html", page(
            site, f"{e(p['title'])} — {e(site['name'])}", p.get("alt") or p["title"], body,
            og_image=f"/img/{p['slug']}-1280.jpg", body_class="photo-page", url=f"/photo/{p['slug']}/"))

    # About
    about = "".join(f"<p>{e(t)}</p>" for t in site.get("about", []))
    write(ROOT / "about" / "index.html", page(
        site, f"About — {e(site['name'])}", "About the photographer behind Clicks by G.",
        f'<section class="band top prose-g"><h1>About</h1>{about}'
        f'<p><a class="g-btn" href="/licensing/">Prints &amp; licensing</a></p></section>',
        current="/about/", url="/about/"))

    # Licensing
    contact = (f'<p>Email <a href="mailto:{e(site["contact_email"])}">{e(site["contact_email"])}</a> '
               f'with the photograph\'s title, the size or use you have in mind, and where you are.</p>'
               if site.get("contact_email") else
               '<p class="todo">Contact email not set yet: add <code>contact_email</code> to '
               '<code>photos/site.json</code>.</p>')
    lic = f"""
    <section class="band top prose-g">
      <h1>Prints &amp; licensing</h1>
      <h2>Fine-art prints</h2>
      <p>Prints are made on archival matte or lustre paper with pigment inks,
      and shipped rolled or framed. Where a photograph has a "Buy a print"
      button that opens a shop page, you can order directly; otherwise send an
      enquiry and I'll reply with sizes and prices.</p>
      <h2>Licensing</h2>
      <p>Photographs can be licensed for editorial use (articles, books,
      education), personal projects, and commercial use (advertising,
      packaging, products). Fees depend on the use, the audience size and the
      term. A licence is granted only once it is agreed in writing and paid.</p>
      <h2>What isn't allowed without a licence</h2>
      <ul>
        <li>Downloading, copying or re-posting the photographs, including with credit</li>
        <li>Using them to train or prompt AI image models</li>
        <li>Printing them, or selling products that use them</li>
      </ul>
      <p>Sharing a link to a page on this site is always welcome.</p>
      <h2 id="enquire">Enquire</h2>
      {contact}
    </section>"""
    write(ROOT / "licensing" / "index.html", page(
        site, f"Prints &amp; licensing — {e(site['name'])}",
        "Buy fine-art prints or license photographs by Clicks by G.", lic,
        current="/licensing/", url="/licensing/"))

    print(f"built {len(photos)} photos in {len(collections)} collections")


if __name__ == "__main__":
    build()
