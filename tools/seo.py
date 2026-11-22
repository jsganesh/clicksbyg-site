"""Page titles and descriptions worded for what people search for:
species, place and kind of photograph first, the brand last."""

DESC_LIMIT = 160  # roughly what Google shows before cutting a description
OFFER = "Fine-art prints and image licensing available."


def clip(text, limit=DESC_LIMIT):
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def subject(p):
    """Common name when known ("Eurasian hoopoe"), else the photo's title."""
    return p.get("species", "").split(" (")[0] or p["title"]


def photo_title(site, p, shared):
    """Species first. When several photos show the same species, their own
    titles ("Brahminy kite, face on") keep the page titles distinct."""
    place = f", {p['place']}" if p.get("place") else ""
    lead = p["title"] if subject(p) in shared else f"{subject(p)} photo"
    return f"{lead}{place} | {site['name']}"


def shared_subjects(photos):
    names = [subject(p) for p in photos]
    return {n for n in names if names.count(n) > 1}


def photo_desc(p):
    where = f" in {p['place']}" if p.get("place") else ""
    when = f", {p['date']}" if p.get("date") else ""
    # The offer goes before the caption so a long caption can't push it out.
    return clip(f"{subject(p)} photographed{where}{when}. {OFFER} {p.get('caption', '')}")


def collection_title(site, c):
    return f"{c['kind']} Photography from {site['region']} | {site['name']}"


def collection_desc(site, c, n):
    return clip(f"{c.get('blurb', '')} {n} {c['kind'].lower()} photographs from "
                f"{site['region']} by {site['name']}, available as prints and for licensing.")
