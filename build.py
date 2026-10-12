"""Builds the Street Jam marketing site into docs/ (served by GitHub Pages).

    python3 build.py            # build
    python3 check_site.py       # verify routes, links, images, metadata

Screenshots, sprites and the logo are read from the game repo: $STREET_JAM_REPO,
default ../Street-Jam (a sibling checkout).

Reads site.config.json. Owner values that do not exist yet (null) are never
replaced by invented ones:
  siteUrl, supportEmail, developerName all set -> indexable site (canonical,
      sitemap, Open Graph, JSON-LD); otherwise the site is built complete but
      noindex, robots.txt keeps crawlers out (except /app-ads.txt) and the
      privacy page shows an "owner details pending" notice.
  playStoreUrl null -> a non-interactive "Coming soon to Google Play" badge;
      set -> a working store link.
  ads "live" -> live-ads privacy/FAQ wording; anything else -> ads-off wording.
Screenshots are the unedited captures in store/screenshots/raw/; vehicle art
is the shipped sprites in assets/images/street_jam/vehicles/. Static files
(styles, fonts, icons, app-ads.txt, og-image) come from static/; the icons and
app-ads.txt are written there by the game repo's tool/gen_launcher_icons.py and
checked by its tool/check_icons.py and tool/check_admob_input.py.
"""
import html
import json
import os
import shutil
import re
import sys
import urllib.parse

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('STREET_JAM_REPO') or os.path.join(os.path.dirname(HERE), 'Street-Jam')
DIST = os.path.join(HERE, 'docs')
RAW = os.path.join(ROOT, 'store', 'screenshots', 'raw')
SPRITES = os.path.join(ROOT, 'assets', 'images', 'street_jam', 'vehicles')
cfg = json.load(open(os.path.join(HERE, 'site.config.json'), encoding='utf-8'))

site = (cfg.get('siteUrl') or '').rstrip('/')
store = cfg.get('playStoreUrl')
email = cfg.get('supportEmail')
dev = cfg.get('developerName')
policy_date = cfg.get('policyDate')
ads_live = cfg.get('ads') == 'live'
audience = cfg.get('audienceStatement')
# GitHub Pages project sites live under /<repo>/; every root-absolute link gets this prefix.
BASE = urllib.parse.urlparse(site).path.rstrip('/')
identity_ready = bool(site and email and dev and policy_date and audience)
indexable = bool(site and email and dev)
esc = html.escape

# ---------------------------------------------------------------- images
SHOTS = {  # id: (raw file, alt text)
    'l12': ('03_level12_day', 'Level 12 by day: red and yellow vehicles on a walled street with arrows showing where each one exits.'),
    'l48d': ('04_level48_day', 'Level 48 by day: a crowded market crossroads with decorated trucks, cars, rickshaws and bikes.'),
    'l48n': ('05_level48_night', 'Level 48 at night: the same crossroads in the dark, with headlights lighting every vehicle.'),
    'l205d': ('06_level205_day', 'Level 205 by day: a plaza board with planted islands between the traffic lanes.'),
    'l205n': ('07_level205_night', 'Level 205 at night: the plaza board in night mode.'),
    'l1': ('02_level1_day', 'Level 1: the first board, a short street with a few vehicles to clear.'),
    'home': ('01_home', 'The Street Jam home screen with Play, Chapters, Garage and Settings buttons.'),
}
WIDTHS = (360, 540, 720)


def build_images():
    os.makedirs(os.path.join(DIST, 'img'), exist_ok=True)
    for key, (raw, _) in SHOTS.items():
        im = Image.open(os.path.join(RAW, raw + '.png')).convert('RGB')
        for w in WIDTHS:
            h = round(im.height * w / im.width)
            r = im.resize((w, h), Image.LANCZOS)
            r.save(os.path.join(DIST, 'img', '%s-%d.webp' % (key, w)), quality=82, method=6)
        im.resize((540, round(im.height * 540 / im.width)), Image.LANCZOS).save(
            os.path.join(DIST, 'img', '%s-540.png' % key), optimize=True)
    for key, f in (('bike', 'bike_red'), ('rickshaw', 'rickshaw_green'), ('car', 'car_blue'), ('truck', 'truck_red_peacock')):
        im = Image.open(os.path.join(SPRITES, f + '.png')).convert('RGBA')
        im.thumbnail((240, 240), Image.LANCZOS)
        im.save(os.path.join(DIST, 'img', 'v-%s.png' % key), optimize=True)
    Image.open(os.path.join(ROOT, 'branding', 'exports', 'logo_master@2x.png')).convert('RGBA').crop(
        (100, 90, 2700, 760)).resize((520, 134), Image.LANCZOS).save(os.path.join(DIST, 'img', 'logo.png'), optimize=True)


def pic(key, sizes='(min-width:820px) 300px, 45vw', eager=False, cls=''):
    alt = SHOTS[key][1]
    ratio = Image.open(os.path.join(RAW, SHOTS[key][0] + '.png'))
    w, h = 540, round(ratio.height * 540 / ratio.width)
    srcset = ', '.join('/img/%s-%d.webp %dw' % (key, x, x) for x in WIDTHS)
    return ('<picture><source type="image/webp" srcset="%s" sizes="%s">'
            '<img src="/img/%s-540.png" width="%d" height="%d" alt="%s"%s></picture>' % (
                srcset, sizes, key, w, h, esc(alt), '' if eager else ' loading="lazy" decoding="async"'))


def fig(key, caption, **kw):
    return '<figure><div class="shot">%s</div><figcaption>%s</figcaption></figure>' % (pic(key, **kw), esc(caption))


# ---------------------------------------------------------------- copy
if ads_live:
    ADS_FAQ = ('The campaign has no ads in its way. Optional rewarded ads, when available, need an internet connection and '
               'unlock cosmetic vehicle skins that you choose in the garage. Levels, undo, restart and hints never need an ad.')
    ADS_PRIVACY = (
        '<h2>Advertising</h2><p>The app can show optional rewarded ads through the Google Mobile Ads SDK (Google AdMob). '
        'Game progress, settings and unlocked skins stay on your device. When an ad is requested, Google may collect and '
        'use your IP address, device and advertising identifiers, ad interactions and diagnostics to serve and measure ads, '
        'prevent fraud and keep its services secure. Where the law requires it, the app asks for your ad privacy choices '
        'through Google\'s User Messaging Platform, and you can review them again from the garage ("Ad privacy options") '
        'where offered. Declining ads never limits levels, hints or undo. Learn more in Google\'s '
        '<a href="https://policies.google.com/technologies/partner-sites">explanation of how Google uses information from '
        'sites or apps that use its services</a>.</p>'
        '<h2>Data the app does not collect itself</h2><p>The app has no accounts, no purchases and no analytics or '
        'crash-reporting SDK of its own.</p>')
    OFFLINE_NOTE = ('Optional rewarded ads for cosmetic skins need an internet connection when they are available; '
                    'the campaign itself does not.')
    SKIN_TEXT = ('Some vehicle skins can be unlocked by watching two optional rewarded ads, when ads are available. They only '
                 'change how vehicles look. Levels, hints and undo never depend on ads.')
else:
    ADS_FAQ = ('The current build has no ads. Optional rewarded ads for cosmetic skins may be offered in a later version; '
               'any change will be described in the store listing and in this site\'s privacy policy before it ships.')
    ADS_PRIVACY = (
        '<h2>Advertising</h2><p>This build shows no ads. It contains no analytics, crash-reporting, account or payment '
        'SDKs, and it does not request network access or the advertising ID. Game progress, settings and unlocked skins '
        'stay on your device. If a later version adds optional rewarded ads, this policy will be updated first.</p>')
    OFFLINE_NOTE = 'The whole campaign works without an internet connection.'
    SKIN_TEXT = ('Four vehicle skins are free to use. More skins are cosmetic extras that a later version may unlock with '
                 'optional rewarded ads. Levels, hints and undo never depend on ads.')

PAGES = {
    'index': ('Street Jam: Traffic Puzzle for Android',
              'Unblock bikes, tuk-tuks, cars and decorated trucks in an offline traffic puzzle. Preview routes, undo moves '
              'and play by day or night.'),
    'how-to-play': ('How to play Street Jam',
                    'Tap a vehicle to preview its route, tap again to drive. Learn how bikes, tuk-tuks, cars and trucks '
                    'move in Street Jam.'),
    'privacy': ('Street Jam privacy policy', 'What data the Street Jam app stores, and how optional ads are handled.'),
    'support': ('Street Jam support', 'Help with Street Jam: progress, blocked vehicles, ads and contact details.'),
}
NAV = [('/', 'Home', 'index'), ('/how-to-play/', 'How to play', 'how-to-play'),
       ('/privacy/', 'Privacy', 'privacy'), ('/support/', 'Support', 'support')]


def cta():
    if store:
        return '<a class="btn" href="%s" rel="noopener">Get it on Google Play</a>' % esc(store)
    return '<span class="soon">Coming soon to Google Play</span>'


def head_tags(slug):
    title, desc = PAGES[slug]
    path = '/' if slug == 'index' else '/%s/' % slug
    t = ['<meta charset="utf-8">', '<meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>%s</title>' % esc(title), '<meta name="description" content="%s">' % esc(desc),
         '<meta name="theme-color" content="#FFC928">',
         '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">',
         '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
         '<link rel="stylesheet" href="/styles.css">',
         '<link rel="preload" href="/fonts/Fredoka-Bold.ttf" as="font" type="font/ttf" crossorigin>']
    if indexable:
        url = site + path
        t += ['<link rel="canonical" href="%s">' % url,
              '<meta property="og:site_name" content="Street Jam">', '<meta property="og:type" content="website">',
              '<meta property="og:title" content="%s">' % esc(title), '<meta property="og:description" content="%s">' % esc(desc),
              '<meta property="og:url" content="%s">' % url, '<meta property="og:image" content="%s/og-image.png">' % site,
              '<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">',
              '<meta property="og:image:alt" content="Street Jam app icon: a decorated truck, a tuk-tuk and a bike on a yellow sunburst">',
              '<meta name="twitter:card" content="summary_large_image">']
        if slug == 'index':
            ld = {'@context': 'https://schema.org', '@type': 'SoftwareApplication', 'name': 'Street Jam',
                  'applicationCategory': 'GameApplication', 'operatingSystem': 'Android', 'url': site + '/'}
            t.append('<script type="application/ld+json">%s</script>' % json.dumps(ld))
    else:
        t.append('<meta name="robots" content="noindex,nofollow">')
    return ''.join(t)


def page(slug, body, hero=''):
    nav = ''.join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if s == slug else '', esc(n)) for h, n, s in NAV)
    header = ('<header class="site-header"><div class="wrap"><a class="brand" href="/" aria-label="Street Jam home">'
              '<img src="/img/logo.png" alt="Street Jam" width="170" height="44"></a>'
              '<nav class="nav" aria-label="Main">%s</nav></div></header>' % nav)
    who = esc(dev) if dev else 'Street Jam'
    contact = ('<a href="mailto:%s">%s</a>' % (esc(email), esc(email))) if email else '<a href="/support/">Support</a>'
    foot = ('<footer class="site-footer"><div class="wrap"><nav aria-label="Footer">%s</nav>'
            '<p>Street Jam is a traffic puzzle for Android.</p>'
            '<p class="fine">&copy; %s &middot; %s</p></div></footer>' % (
                ''.join('<a href="%s">%s</a>' % (h, esc(n)) for h, n, _ in NAV[1:]), who, contact))
    return ('<!doctype html><html lang="en"><head>%s</head><body><a class="skip" href="#main">Skip to content</a>%s'
            '%s<main id="main">%s</main>%s</body></html>' % (head_tags(slug), header, hero, body, foot))


# ---------------------------------------------------------------- pages
hero = '''<div class="hero"><div class="wrap"><div>
<h1>Clear the street, one vehicle at a time.</h1>
<p class="lead">Street Jam is a traffic puzzle with bikes, tuk-tuks, cars and colourful decorated trucks. Look ahead, find a clear
route and choose the right departure order to untangle the jam.</p>
<div class="actions">%s<a class="btn alt" href="/how-to-play/">How to play</a></div>
<p class="fine">Android. %s</p></div>
<div class="phones" aria-label="Gameplay screenshots">%s%s</div></div></div>''' % (
    cta(), esc(OFFLINE_NOTE), fig('l12', 'Level 12, day', eager=True, sizes='(min-width:820px) 220px, 42vw'),
    fig('l48n', 'Level 48, night', eager=True, sizes='(min-width:820px) 220px, 42vw'))

VEH = [('bike', 'Bikes', 'Narrow bike lanes are theirs alone. A bike can slip out where nothing else fits.', 'A red courier bike'),
       ('rickshaw', 'Tuk-tuks', 'Rickshaws follow tight marked turns, so their whole route matters.', 'A green tuk-tuk'),
       ('car', 'Cars', 'Cars need a wider clear lane and a longer run to the exit.', 'A blue car'),
       ('truck', 'Decorated trucks', 'Long, colourful trucks need the entire path clear, tail included.', 'A red decorated truck')]
index_body = '''<section class="wrap" aria-labelledby="v"><h2 id="v">Different vehicles, different challenges</h2>
<p class="lead">Bikes fit through narrow lanes, while cars and long trucks need more space. Follow the marked routes and make
room for vehicles that cannot leave yet.</p>
<div class="vehicles">%s</div></section>
<div class="band"><section class="wrap split" aria-labelledby="r"><div><h2 id="r">See your route before you drive</h2>
<p>Tap a vehicle to preview its route, including turns. Tap again to send it on its way. If another vehicle blocks the
route, the game shows what is in the way.</p>
<p>There is no timer rushing your decisions. Use undo, restart and hints when you want another approach.</p>
<p><a class="btn alt" href="/how-to-play/">Read the full guide</a></p></div>
<div class="pair">%s%s</div></section></div>
<section class="wrap split rev" aria-labelledby="dn"><div><h2 id="dn">Day and night</h2>
<p>Switch between daylight and night mode, with headlights that follow the vehicles as they turn.</p>
<p>Larger boards support zooming and panning so you can inspect the traffic.</p></div>
<div class="pair">%s%s</div></section>
<div class="band"><section class="wrap" aria-labelledby="o"><h2 id="o">Offline campaign, optional cosmetic extras</h2>
<div class="split"><div><p>Play campaign puzzles without an internet connection, in layouts set around courtyards, truck yards and
busy market streets.</p></div><div><p>%s</p></div></div></section></div>
<section class="wrap" aria-labelledby="g"><h2 id="g">From the game</h2>
<p class="fine">Real screenshots from the running app. Scroll sideways to see more.</p>
<div class="gallery" role="region" aria-label="Screenshot gallery" tabindex="0">%s%s%s%s%s</div></section>
<section class="wrap faq" aria-labelledby="f"><h2 id="f">Questions</h2>
<details><summary>Does it work offline?</summary><p>Yes. The campaign works without an internet connection. %s</p></details>
<details><summary>Which devices does it run on?</summary><p>Street Jam is built for Android phones and tablets.</p></details>
<details><summary>Are there ads?</summary><p>%s</p></details>
<details><summary>Do I need an account?</summary><p>No. Progress is saved on your device.</p></details>
<details><summary>Where can I get help?</summary><p>See the <a href="/support/">support page</a>.</p></details></section>''' % (
    ''.join('<div class="card"><div class="art"><img src="/img/v-%s.png" alt="%s" width="104" height="104" loading="lazy"></div>'
            '<h3>%s</h3><p>%s</p></div>' % (k, esc(a), esc(n), esc(t)) for k, n, t, a in VEH),
    '<div class="shot">%s</div>' % pic('l1', sizes='230px'), '<div class="shot">%s</div>' % pic('l12', sizes='230px'),
    '<div class="shot">%s</div>' % pic('l48d', sizes='230px'), '<div class="shot">%s</div>' % pic('l48n', sizes='230px'),
    esc(SKIN_TEXT),
    fig('home', 'Home screen', sizes='240px'), fig('l205d', 'Level 205, day', sizes='240px'),
    fig('l205n', 'Level 205, night', sizes='240px'), fig('l48d', 'Level 48, day', sizes='240px'),
    fig('l1', 'Level 1', sizes='240px'), esc(OFFLINE_NOTE), esc(ADS_FAQ))

how_body = '''<section class="wrap prose"><h1>How to play</h1>
<p class="lead">Every board is a traffic jam. Send each vehicle out the way its arrow points, in an order that never leaves anything
stuck.</p>
<ol class="steps">
<li><strong>Read the arrows.</strong> Each vehicle has an arrow that shows the direction it drives.</li>
<li><strong>Tap to preview.</strong> Tap a vehicle to see its whole route, including every turn.</li>
<li><strong>Tap again to drive.</strong> If the route is clear the vehicle leaves. If not, the game shows what is in the way.</li>
<li><strong>Mind the vehicle type.</strong> Bikes use narrow lanes, tuk-tuks take tight turns, and cars and long trucks need more room.</li>
<li><strong>Take your time.</strong> There is no timer. Undo and restart whenever you like, and use a hint if you are stuck.</li>
<li><strong>Look around.</strong> On larger boards, pinch to zoom and drag to pan.</li></ol>
<p>Levels, hints and undo never depend on ads. %s</p>
<div class="phones" style="margin:28px 0">%s%s</div>
<p><a class="btn" href="/">Back to home</a></p></section>''' % (
    esc(OFFLINE_NOTE), fig('l1', 'Level 1', sizes='(min-width:820px) 240px, 44vw'),
    fig('l48d', 'A busier board', sizes='(min-width:820px) 240px, 44vw'))

if identity_ready:
    notice = ''
else:
    notice = ('<div class="notice" role="note"><strong>Draft.</strong> The developer name, contact address, effective date or '
              'audience statement is not yet filled in, so this policy is not final and this site is not indexed.</div>')
contact_line = ('%s, <a href="mailto:%s">%s</a>' % (esc(dev), esc(email), esc(email))) if dev and email else \
    'The developer\'s name and contact address will be listed here before release.'
privacy_body = '''<section class="wrap prose"><h1>Privacy policy</h1>%s
<p class="fine">Effective date: %s</p>
<p>This policy describes the Street Jam app as currently built. It is updated whenever an SDK or online feature is added.</p>
<h2>What stays on your device</h2><p>Game progress, settings, unlocked skins and the current level attempt are saved only on your
device. Uninstalling the app or clearing its data removes them.</p>
%s
<h2>Accounts and purchases</h2><p>Street Jam has no accounts or login and no in-app purchases.</p>
<h2>Children</h2><p>%s</p>
<h2>Contact</h2><p>%s</p></section>''' % (
    notice, esc(policy_date) if policy_date else 'to be set at publication', ADS_PRIVACY,
    esc(audience) if audience else 'The developer has not yet published an audience statement. This section will be completed before release.',
    contact_line)

contact_p = ('<p>Email <a href="mailto:%s">%s</a>.</p>' % (esc(email), esc(email))) if email else \
    '<p>The support email address will be listed here before release.</p>'
support_body = '''<section class="wrap prose"><h1>Support</h1>%s
<section class="faq" aria-label="Common questions">
<details open><summary>My progress disappeared</summary><p>Progress is saved on your device after every move. Uninstalling the app or clearing
its data removes it, and it is not stored online.</p></details>
<details><summary>A vehicle will not move</summary><p>Something is on its route. Tap the vehicle to preview the route; the game shows what is in
the way.</p></details>
<details><summary>I am stuck</summary><p>Use undo or restart as often as you like, or tap the hint button. Hints are free.</p></details>
<details><summary>Ads and skins</summary><p>%s</p></details>
<details><summary>Ad privacy choices</summary><p>%s</p></details></section></section>''' % (
    contact_p, esc(SKIN_TEXT),
    'Where the app shows them, you can reopen your ad privacy choices from the garage ("Ad privacy options").' if ads_live
    else 'The current build shows no ads, so there are no ad choices to make.')

notfound_body = '''<section class="wrap prose"><h1>Page not found</h1><p>That page does not exist. Try the
<a href="/">home page</a> or <a href="/how-to-play/">how to play</a>.</p></section>'''
PAGES['404'] = ('Page not found | Street Jam', 'This page does not exist.')


def write(rel, text):
    p = os.path.join(DIST, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if BASE and rel.endswith('.html'):
        text = re.sub(r'((?:href|src)="|srcset="|, )/(?!/)', lambda m: m.group(1) + BASE + '/', text)
    open(p, 'w', encoding='utf-8').write(text)


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)
    shutil.copytree(os.path.join(HERE, 'static'), DIST, dirs_exist_ok=True)
    open(os.path.join(DIST, '.nojekyll'), 'w').close()  # GitHub Pages: serve files as-is
    build_images()
    write('index.html', page('index', index_body, hero))
    write('how-to-play/index.html', page('how-to-play', how_body))
    write('privacy/index.html', page('privacy', privacy_body))
    write('support/index.html', page('support', support_body))
    nf = page('404', notfound_body).replace('<meta name="robots"', '<meta name="robots"')
    if indexable:
        nf = nf.replace('</head>', '<meta name="robots" content="noindex"></head>', 1)
    write('404.html', nf)
    routes = ['/', '/how-to-play/', '/privacy/', '/support/']
    if indexable:
        write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n'
              % ''.join('<url><loc>%s%s</loc></url>' % (site, r) for r in routes))
        write('robots.txt', 'User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n' % site)
    else:
        write('robots.txt', 'User-agent: *\nAllow: /app-ads.txt\nDisallow: /\n')
    missing = [k for k, v in (('siteUrl', site), ('supportEmail', email), ('developerName', dev),
                              ('policyDate', policy_date), ('audienceStatement', audience), ('playStoreUrl', store)) if not v]
    print('built %s: %s' % (DIST, 'INDEXABLE' if indexable else 'NOINDEX (owner inputs pending)'))
    if missing:
        print('pending owner inputs in site.config.json: ' + ', '.join(missing))
    return 0


if __name__ == '__main__':
    sys.exit(main())
