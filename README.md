# Street Jam website

Landing site, privacy policy and support page for the Street Jam Android game.
Live at **https://muhammadbiilal.github.io/Street-Jam-Website/** (GitHub Pages, branch `main`, folder `/docs`).

Pages: `/`, `/how-to-play/`, `/privacy/` (the Google Play privacy policy URL), `/support/`, `/404.html`.

## Build and publish

    python3 build.py        # renders docs/ (needs Python 3 + Pillow)
    python3 check_site.py   # routes, links, images, alt text, titles, robots, app-ads
    git add -A && git commit -m "Rebuild site" && git push

`docs/` is the built output and **is committed**: GitHub Pages serves it as-is, with no Actions workflow.
One-time setup: repo Settings → Pages → Source "Deploy from a branch", `main`, `/docs`.

## Coupling with the game repo (`../Street-Jam`)

`build.py` reads from the game repo (`$STREET_JAM_REPO`, default the sibling folder `../Street-Jam`):

| read from game repo | used for |
|---|---|
| `store/screenshots/raw/0{1..7}_*.png` | screenshots |
| `assets/images/street_jam/vehicles/*.png` | vehicle cards |
| `branding/exports/logo_master@2x.png` | header logo |

The game repo writes into or checks this repo (path `$STREET_JAM_WEBSITE`, default `../Street-Jam-Website`, set in
the game repo's `tool/website.py`):

| game repo tool | touches here |
|---|---|
| `tool/gen_launcher_icons.py` | writes `static/{favicon,favicon-32,apple-touch-icon,icon-192,og-image}.png` |
| `tool/check_icons.py` | checks those icons |
| `tool/check_admob_input.py` | `static/app-ads.txt` must match `config/admob_owner_input.json` |

Whenever screenshots, icons, the logo, ads or data handling change in the game, rebuild and push this site.
The game repo's `docs/WEBSITE.md` mirrors this list.

## Owner inputs (`site.config.json`; nothing is invented)

| key | while null | when set |
|---|---|---|
| `supportEmail`, `developerName` | whole site `noindex`, no canonical/sitemap/OG | indexable, canonical, sitemap, Open Graph, JSON-LD |
| `policyDate`, `audienceStatement` | privacy page shows a **Draft** notice | final privacy policy |
| `playStoreUrl` | "Coming soon to Google Play" badge | working store link |
| `ads` | ads-off wording | `"live"` gives the Google Mobile Ads / UMP wording; set it before uploading a live-ads build |

The Play Console privacy policy URL is `https://muhammadbiilal.github.io/Street-Jam-Website/privacy/`. Play rejects a
policy that is a draft, so fill `developerName`, `supportEmail`, `policyDate` and `audienceStatement` first, and keep
the wording consistent with the Data safety form.

## Known limit: app-ads.txt

AdMob only reads `app-ads.txt` from the **root** of the developer website listed on Play. A project site lives under
`/Street-Jam-Website/`, so `docs/app-ads.txt` is not at a root. For live ads, either point a custom domain at this
repo (Settings → Pages → Custom domain, then set `siteUrl` to it) or publish the file from a
`muhammadbiilal.github.io` user-site repo.
