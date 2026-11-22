#!/usr/bin/env python3
"""Check the site before pushing:  python3 tools/check_site.py

1. Encoding drops metadata (GPS especially), applies camera rotation and
   never upscales, tested on a synthetic export in a temp folder.
2. Every internal link and image on every page resolves to a file, and every
   generated page carries the CSP and no inline styles (which the CSP blocks).
"""
import re
import sys
import tempfile
from pathlib import Path

from PIL import Image

from images import WIDTHS, encode, outputs
from publish import visible_collections

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ("index.html", "about", "collections", "licensing", "photo")
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
        Image.new("RGB", (1500, 1000), (200, 80, 40)).save(tmp / "src.jpg", exif=exif)
        photo = {"slug": "t"}
        encode(photo, tmp / "src.jpg", tmp / "img")
        check(photo["w"] == 1000 and photo["h"] == 1500, "rotation not applied to size")
        for out in outputs("t", tmp / "img"):
            with Image.open(out) as im:
                check(not im.getexif(), f"metadata left in {out.name}")
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


if __name__ == "__main__":
    check_encoding()
    check_collections()
    check_pages()
    print("\n".join(failures) or f"ok: encoding and {sum(1 for _ in site_pages())} pages checked")
    sys.exit(1 if failures else 0)
