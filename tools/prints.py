"""The /prints/ page: a price list and a pre-filled order email for each photo."""
import re
from html import escape as e

from images import picture
from render import PRINT_FORM, enquire_href, fill

CURRENCY = re.compile(r"[A-Z]{3}")
FORMATS = ("unframed", "framed")


def validate(prints):
    """Prices are printed on the page and quoted in orders, so a typo in
    site.json stops the build rather than going live."""
    if not CURRENCY.fullmatch(prints.get("currency", "")):
        return "prints.currency must be a three-letter code like NZD"
    if not prints.get("sizes"):
        return "prints.sizes is empty"
    for s in prints["sizes"]:
        for f in FORMATS:
            price = s.get(f)
            if not isinstance(price, int) or isinstance(price, bool) or price <= 0:
                return f"prints size {s.get('name')!r}: {f} price must be a whole number above 0"
    return None


def order_form(prints, overseas=False):
    # {photo} stays a placeholder for enquire_href to fill per photo.
    sizes = ", ".join(s["name"] for s in prints["sizes"])
    # Overseas postage varies by country, so those orders need the country to quote.
    where = "Country:\nDelivery address:\n" if overseas else f"Delivery address in {prints['ships_to']}:\n"
    return ("Photo: {photo}\n\n"
            f"Size ({sizes}):\n"
            "Unframed or framed:\n"
            "Your name:\n" + where)


def price_rows(prints):
    cur = prints["currency"]
    return "".join(f'<tr><th scope="row">{e(s["name"])}</th>'
                   + "".join(f"<td>${s[f]} {cur}</td>" for f in FORMATS) + "</tr>"
                   for s in prints["sizes"])


def cards(site, prints, photos):
    local, overseas = order_form(prints), order_form(prints, overseas=True)
    return "".join(
        f'<li class="pr-card p-{p["slug"]}" id="{p["slug"]}">'
        f'{picture(p, "(max-width: 700px) 100vw, 33vw", cls="pr-img")}'
        f'<h3>{e(p["title"])}</h3>'
        f'<a class="g-btn" href="{e(enquire_href(site, "Print order: " + p["title"], local, p["title"]))}">'
        f'Order this print</a>'
        f'<a class="pr-abroad" href="{e(enquire_href(site, "Overseas print order: " + p["title"], overseas, p["title"]))}">'
        f'Outside {e(prints["ships_to"])}? Ask for a delivered price</a></li>'
        for p in photos)


def body(site, prints, photos):
    return fill("prints.html", currency=e(prints["currency"]), ships_to=e(prints["ships_to"]),
                rows=price_rows(prints), cards=cards(site, prints, photos),
                overseas_href=e(enquire_href(site, "Overseas print order",
                                             order_form(prints, overseas=True))),
                quote_href=e(enquire_href(site, "Print quote", PRINT_FORM)))
