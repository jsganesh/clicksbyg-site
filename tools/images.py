"""Web copies of photo exports, and the <picture> markup that serves them."""
import html

from PIL import Image, ImageOps

WIDTHS = (640, 1280, 2048)
FORMATS = (("webp", "WEBP", {"quality": 80, "method": 6}),
           ("jpg", "JPEG", {"quality": 82, "optimize": True, "progressive": True}))


def outputs(slug, img_dir):
    return [img_dir / f"{slug}-{w}.{ext}" for w in WIDTHS for ext, _, _ in FORMATS]


def encode(photo, src, img_dir):
    """Write any stale web copies and add w, h, ar and bg to photo."""
    with Image.open(src) as im:
        # Apply the camera's rotation now, because the EXIF that holds it is dropped.
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        if _stale(src, outputs(photo["slug"], img_dir)):
            _write_sizes(im, photo["slug"], img_dir)
            print("encoded", photo["slug"])
        avg = im.resize((1, 1), Image.LANCZOS).getpixel((0, 0))
    photo.update(w=w, h=h, ar=round(w / h, 4), bg="#%02x%02x%02x" % avg)


def _stale(src, outs):
    mtime = src.stat().st_mtime
    return any(not o.exists() or o.stat().st_mtime < mtime for o in outs)


def _write_sizes(im, slug, img_dir):
    img_dir.mkdir(exist_ok=True)
    w, h = im.size
    for tw in WIDTHS:
        # Never upscale: small exports are saved at their own size.
        r = im.resize((tw, round(h * tw / w)), Image.LANCZOS) if tw < w else im
        for ext, fmt, opts in FORMATS:
            # No exif= argument, so Pillow writes pixels only: no GPS, no serials.
            r.save(img_dir / f"{slug}-{tw}.{ext}", fmt, **opts)


def picture(p, sizes, cls="", loading="lazy", priority=False):
    def srcset(ext):
        return ", ".join(f"/img/{p['slug']}-{w}.{ext} {min(w, p['w'])}w" for w in WIDTHS)
    fetch = ' fetchpriority="high"' if priority else ""
    alt = html.escape(p.get("alt") or p["title"])
    return (
        f'<picture class="{cls}">'
        f'<source type="image/webp" srcset="{srcset("webp")}" sizes="{sizes}">'
        f'<img src="/img/{p["slug"]}-1280.jpg" srcset="{srcset("jpg")}" sizes="{sizes}" '
        f'width="{p["w"]}" height="{p["h"]}" alt="{alt}" '
        f'loading="{loading}" decoding="async"{fetch}>'
        f"</picture>"
    )
