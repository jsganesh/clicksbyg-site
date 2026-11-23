#!/usr/bin/env python3
"""Check the site before pushing:  python3 tools/check_site.py

1. Encoding keeps only artist and copyright (no GPS or camera details),
   applies camera rotation and never upscales, tested on a synthetic export in a temp folder.
2. Every internal link and image on every page resolves to a file, and every
   generated page carries the CSP and no inline styles (which the CSP blocks).
3. Photo arrows lead to the same photos as the pager below them.
"""
import html
import json
import re
import sys
import tempfile
from pathlib import Path

from PIL import Image

from images import COPYRIGHT, WIDTHS, credit_exif, encode, outputs
import seo
from publish import FOCUS, HANDLE, visible_collections

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ("index.html", "404.html", "about", "collections", "licensing", "contact", "photo")
SKIP_DIRS = {".git", ".claude", "tools", "photos", "node_modules"}
failures = []


def check(ok, msg):
    if not ok:
        failures.append(msg)


def check_encoding():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        exif = Image.Exif()
        exif[0x0112] = 6  # Orientation: rotate 90° clockwise to display
        exif[0x8825] = {1: "N", 2: (51.0, 30.0, 0.0)}  # GPS block
        exif[0x010F], exif[0x0110] = "Sony", "ILCE-6700"  # make, model
        Image.new("RGB", (1500, 1000), (200, 80, 40)).save(tmp / "src.jpg", exif=exif)
        photo = {"slug": "t"}
        encode(photo, tmp / "src.jpg", tmp / "img", credit_exif("Test", "Copyright Test"))
        check(photo["w"] == 1000 and photo["h"] == 1500, "rotation not applied to size")
        for out in outputs("t", tmp / "img"):
            with Image.open(out) as im:
                kept = im.getexif()
                check(set(kept) == {0x013B, COPYRIGHT}, f"{out.name} keeps tags {sorted(kept)}")
                check(kept.get(COPYRIGHT) == "Copyright Test", f"{out.name} lacks copyright")
                check(im.width <= 1000, f"{out.name} upscaled to {im.width}px")
                check(im.height > im.width, f"{out.name} not rotated")
        check(len(outputs("t", tmp / "img")) == len(WIDTHS) * 2, "wrong number of copies")


def check_collections():
    photos = [{"slug": "a", "collection": "birds"}, {"slug": "b", "collection": "birds"}]
    data = {"collections": [{"slug": "birds", "cover": "missing"}, {"slug": "cities", "cover": ""}],
            "by_coll": {"birds": photos, "cities": []}}
    shown = visible_collections(data)
    check([c["slug"] for c in shown] == ["birds"], "empty collection not hidden")
    check(shown[0]["cover"] == "a", "missing cover not replaced by first photo")


def check_focus():
    for ok in ("50% 50%", "0% 100%", "63% 41%"):
        check(FOCUS.fullmatch(ok), f"focus {ok!r} wrongly rejected")
    for bad in ("50%", "101% 0%", "50% 50%;}body{display:none", "center"):
        check(not FOCUS.fullmatch(bad), f"focus {bad!r} wrongly accepted")


def check_handle():
    check(HANDLE.fullmatch("clicks.by_g"), "valid Instagram handle rejected")
    for bad in ("@clicks.by_g", "instagram.com/clicks.by_g", 'x"><script>', ""):
        check(not HANDLE.fullmatch(bad), f"Instagram handle {bad!r} wrongly accepted")


def site_pages():
    for path in ROOT.rglob("*.html"):
        if not SKIP_DIRS & set(path.relative_to(ROOT).parts):
            yield path


def resolves(url):
    target = ROOT / url.split("#")[0].split("?")[0].lstrip("/")
    return target.is_file() or (target / "index.html").is_file()


def check_pages():
    for path in site_pages():
        text, rel = path.read_text(), path.relative_to(ROOT)
        for url in re.findall(r'(?:href|src|srcset)="(/[^"]*)"', text):
            for part in url.split(", "):
                link = part.split(" ")[0]
                check(resolves(link), f"{rel}: broken link {link}")
        if rel.parts[0] in GENERATED:
            check("Content-Security-Policy" in text, f"{rel}: no CSP")
            check(" style=" not in text, f"{rel}: inline style blocked by CSP")
        if rel.parts[0] == "photo":
            check_licensable(rel, text)
            check_arrows(rel, text)
        check('rel="icon"' in text, f"{rel}: no favicon link")
        if "noindex" not in text:
            check_search_text(rel, text)


titles = {}


def check_search_text(rel, text):
    title = re.search(r"<title>(.*?)</title>", text).group(1)
    desc = re.search(r'<meta name="description" content="([^"]*)"', text)
    check(title not in titles, f"{rel}: same title as {titles.get(title)}")
    titles[title] = rel
    # Measured unescaped: "&amp;" is one character to a reader.
    length = len(html.unescape(desc.group(1))) if desc else 0
    check(0 < length <= seo.DESC_LIMIT, f"{rel}: description is {length} characters")


def check_arrows(rel, text):
    """The arrows on the photo must lead where the pager below does."""
    for side in ("prev", "next"):
        arrow = re.search(rf'class="photo-nav {side}" href="([^"]+)"', text)
        pager = re.search(rf'rel="{side}" href="([^"]+)"', text)
        check((arrow and arrow.group(1)) == (pager and pager.group(1)), f"{rel}: {side} arrow doesn't match the pager")


def check_licensable(rel, text):
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
    try:
        data = json.loads(m.group(1)) if m else {}
    except ValueError:
        data = {}
    check(data.get("acquireLicensePage") and data.get("license"), f"{rel}: no licensable data")


def check_sitemap():
    xml = (ROOT / "sitemap.xml").read_text()
    locs = re.findall(r"<(?:image:)?loc>https://clicksbyg\.com(/[^<]*)</", xml)
    for path in locs:
        check(resolves(path), f"sitemap: {path} doesn't exist")
    pages = sum(1 for p in site_pages() if p.name == "index.html")
    check(xml.count("<url>") == pages, f"sitemap lists {xml.count('<url>')} of {pages} pages")
    check("Sitemap: https://clicksbyg.com/sitemap.xml" in (ROOT / "robots.txt").read_text(),
          "robots.txt doesn't point at the sitemap")


if __name__ == "__main__":
    check_encoding()
    check_collections()
    check_focus()
    check_handle()
    check_pages()
    check_sitemap()
    print("\n".join(failures) or f"ok: encoding and {sum(1 for _ in site_pages())} pages checked")
    sys.exit(1 if failures else 0)
