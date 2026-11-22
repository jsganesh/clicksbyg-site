"""sitemap.xml and robots.txt for clicksbyg.com."""
from xml.sax.saxutils import escape

SITE = "https://clicksbyg.com"
# Folders that hold source, not pages; _config.yml keeps them off the site.
NOT_PUBLISHED = {".git", ".claude", "tools", "photos", "node_modules"}
# The licensing terms forbid AI training, so the crawlers that collect
# training data are turned away. Search engines are unaffected.
AI_CRAWLERS = ("GPTBot", "ClaudeBot", "CCBot", "Google-Extended", "Applebot-Extended",
               "Bytespider", "meta-externalagent")


def page_urls(root):
    """Every published page, found on disk so hand-written pages count too."""
    for index in sorted(root.rglob("index.html")):
        rel = index.relative_to(root)
        if not NOT_PUBLISHED & set(rel.parts):
            yield "/" + "".join(f"{part}/" for part in rel.parts[:-1])


def sitemap_xml(urls, photos):
    images = {f"/photo/{p['slug']}/": p for p in photos}
    entries = []
    for url in urls:
        p = images.get(url)
        img = (f"<image:image><image:loc>{SITE}/img/{p['slug']}-2048.jpg</image:loc></image:image>"
               if p else "")
        entries.append(f"  <url><loc>{escape(SITE + url)}</loc>{img}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
            + "\n".join(entries) + "\n</urlset>\n")


def robots_txt():
    blocked = "".join(f"User-agent: {bot}\nDisallow: /\n\n" for bot in AI_CRAWLERS)
    return f"{blocked}User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"


def build(root, photos):
    (root / "sitemap.xml").write_text(sitemap_xml(list(page_urls(root)), photos))
    (root / "robots.txt").write_text(robots_txt())
