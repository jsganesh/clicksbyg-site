# clicksbyg.com

Photography by Clicks by G, plus the support pages for its apps. Served by
GitHub Pages at clicksbyg.com. Plain HTML, no build step on the server:
the photo pages are generated locally and committed.

## Photo pages (generated)

- `/`: home, with hero, collections and recent work
- `/collections/`, `/collections/<slug>/`, `/photo/<slug>/`
- `/about/`, `/licensing/`
- `img/`: web copies (640/1280/2048 px, WebP + JPEG, metadata stripped)
- `assets/photos.css`: per-photo aspect ratio and placeholder colour

Don't edit these by hand. Change `photos/site.json` and run the script.

### Adding photos

1. Export a full-size JPEG (or TIFF/PNG) from your editor into `photos/source/`.
   This folder is git-ignored: originals stay on your Mac or Pi, never on GitHub.
2. Add an entry to `photos/site.json` (`slug`, `file`, `title`, `collection`,
   `alt`, optional `caption`, `place`, `date`, `camera`, `lens`, `settings`,
   `print_url`, `license_url`). Order in the list is the order on the site;
   the first `"featured": true` photo is the home-page hero.
3. Run `python3 tools/publish.py` (needs Pillow: `pip install -r requirements.txt`).
4. Preview, then commit and push.

`print_url` / `license_url` can be a Stripe Payment Link, a Lemon Squeezy or
Gumroad product, or a print-on-demand shop page. Without them, the buttons
email `site.contact_email`, or go to `/licensing/` if no email is set.

The sample landscapes in `photos/source/samples/` are drawn by
`tools/make_samples.py`. Replace them before going live.

## App pages (hand-written)

- `/apps/`: list of apps
- `/philatally/`: PhilaTally overview, `support/` and `privacy/`
- `/stampalbum-pro/`: StampAlbum Pro overview, downloads, privacy and support

These URLs are linked from the App Store and must not move.
The PhilaTally privacy and support text is copied from the
`philatally-privacy` repo, which the app still links to. Change both until
the app links point here.

## Preview

    python3 -m http.server 8765 --bind 127.0.0.1
