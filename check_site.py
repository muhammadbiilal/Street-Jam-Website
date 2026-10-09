"""Verifies docs/ (the built site): routes, internal links/anchors, images, metadata, robots, app-ads.txt.

    python3 build.py && python3 check_site.py
Exit 0 only when everything resolves. Nothing is fetched from the network.
"""
import json
import os
import re
import sys
import urllib.parse
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, 'docs')
cfg = json.load(open(os.path.join(HERE, 'site.config.json')))
BASE = urllib.parse.urlparse(cfg.get('siteUrl') or '').path.rstrip('/')
problems = []


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.imgs, self.meta, self.h1, self.title = [], set(), [], {}, 0, ''
        self.links, self._t = [], False
        self.lang = None

    def handle_starttag(self, tag, a):
        a = dict(a)
        if a.get('id'):
            self.ids.add(a['id'])
        if tag == 'html':
            self.lang = a.get('lang')
        if tag == 'h1':
            self.h1 += 1
        if tag == 'title':
            self._t = True
        if tag == 'a' and a.get('href'):
            self.refs.append(a['href'])
        if tag == 'link' and a.get('href'):
            self.refs.append(a['href'])
            self.links.append(a)
        if tag in ('img', 'source', 'script'):
            for k in ('src', 'srcset'):
                if a.get(k):
                    for part in a[k].split(','):
                        self.refs.append(part.strip().split(' ')[0])
        if tag == 'img':
            self.imgs.append(a)
        if tag == 'meta' and a.get('name'):
            self.meta[a['name']] = a.get('content', '')
        if tag == 'meta' and a.get('property'):
            self.meta[a['property']] = a.get('content', '')

    def handle_data(self, d):
        if self._t:
            self.title += d

    def handle_endtag(self, tag):
        if tag == 'title':
            self._t = False


def resolve(url):
    path = url.split('#')[0].split('?')[0]
    if BASE and url.startswith('/'):
        if not (path + '/').startswith(BASE + '/'):
            problems.append('link outside %s/: %s' % (BASE, url))
        path = path[len(BASE):] or '/'
    p = os.path.join(DIST, path.lstrip('/'))
    if path.endswith('/') or os.path.isdir(p):
        p = os.path.join(p, 'index.html')
    return p


pages = {}
for root, _, files in os.walk(DIST):
    for f in files:
        if f.endswith('.html'):
            rel = os.path.relpath(os.path.join(root, f), DIST).replace(os.sep, '/')
            p = P()
            p.feed(open(os.path.join(root, f), encoding='utf-8').read())
            pages[rel] = p
for need in ('index.html', 'how-to-play/index.html', 'privacy/index.html', 'support/index.html', '404.html'):
    if need not in pages:
        problems.append('missing page ' + need)
indexable = bool(cfg.get('siteUrl') and cfg.get('supportEmail') and cfg.get('developerName'))
for rel, p in pages.items():
    if p.lang != 'en':
        problems.append(f'{rel}: html lang')
    if BASE + '/styles.css' not in p.refs:
        problems.append(f'{rel}: no stylesheet link at {BASE}/styles.css')
    if not p.title.strip() or len(p.title) > 70:
        problems.append(f'{rel}: title missing/too long')
    if not p.meta.get('description'):
        problems.append(f'{rel}: no meta description')
    if p.h1 != 1:
        problems.append(f'{rel}: {p.h1} h1 elements')
    has_noindex = 'noindex' in p.meta.get('robots', '')
    if not indexable and not has_noindex:
        problems.append(f'{rel}: placeholders remain but page is indexable')
    if indexable and rel != '404.html' and (has_noindex or 'og:image' not in p.meta):
        problems.append(f'{rel}: indexable site lacks index/og metadata')
    if not indexable and any(l.get('rel') == 'canonical' for l in p.links):
        problems.append(f'{rel}: canonical while noindex')
    for img in p.imgs:
        if not img.get('alt', '').strip():
            problems.append(f'{rel}: image without alt {img.get("src")}')
        if not (img.get('width') and img.get('height')):
            problems.append(f'{rel}: image without dimensions {img.get("src")}')
    for ref in p.refs:
        if re.match(r'^(https?:|mailto:|tel:|data:)', ref):
            continue
        if ref.startswith('#'):
            if ref[1:] and ref[1:] not in p.ids:
                problems.append(f'{rel}: dead anchor {ref}')
            continue
        target = resolve(ref)
        if not os.path.isfile(target):
            problems.append(f'{rel}: broken reference {ref}')
        elif '#' in ref:
            frag = ref.split('#')[1]
            tp = pages.get(os.path.relpath(target, DIST))
            if tp and frag not in tp.ids:
                problems.append(f'{rel}: dead anchor {ref}')
text = {rel: open(os.path.join(DIST, rel), encoding='utf-8').read() for rel in pages}
for rel, t in text.items():
    for bad in ('TODO', '[owner', 'Lorem', 'example.com', 'Coming soon' if cfg.get('playStoreUrl') else '@@'):
        if bad in t:
            problems.append(f'{rel}: contains {bad!r}')
    if cfg.get('playStoreUrl') is None and re.search(r'<a[^>]*>\s*Get it on Google Play', t):
        problems.append(f'{rel}: store button without a store URL')
aa = open(os.path.join(DIST, 'app-ads.txt')).read().strip()
if not re.fullmatch(r'google\.com, pub-\d{16}, DIRECT, f08c47fec0942fa0', aa):
    problems.append('app-ads.txt malformed')
robots = open(os.path.join(DIST, 'robots.txt')).read()
if not indexable and 'Disallow: /' not in robots:
    problems.append('robots.txt should disallow while placeholders remain')
if 'Allow: /app-ads.txt' not in robots and not indexable:
    problems.append('robots.txt must keep /app-ads.txt fetchable')
if indexable and not os.path.isfile(os.path.join(DIST, 'sitemap.xml')):
    problems.append('sitemap.xml missing')
for p in problems:
    print('  - ' + p)
print('site: %d pages, %s' % (len(pages), 'REFUSED' if problems else 'OK'))
sys.exit(1 if problems else 0)
