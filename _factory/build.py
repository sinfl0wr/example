#!/usr/bin/env python3
"""Build personal demo sites.

  python3 build.py --relayout NAME <slug> [<slug> ...]   (new look for demos already built; no network)
  python3 build.py [--layout NAME] [--auto] sites/<slug>.js [...]   ->  <repo root>/<slug>/index.html (+ img/)

Layouts (see LAYOUTS): the site file's `layout` field wins, then --layout, then the saved choice in layouts.json,
then --auto (picks the least-used new layout and avoids the ones already used in the same town), else "ring"
(the original look, so the 72 existing demos stay as they are).

A site file is a JS object literal written by the copy agent (see RULES.md). This script adds the
standard demo texts, downloads and crops the business's own photos, and renders the template.
"""
import html, io, json, pathlib, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).parent
LAYOUT_FILE = ROOT / 'layouts.json'  # slug -> layout, so a rebuild keeps the look and --auto can rotate

GF = 'https://fonts.googleapis.com/css2?{}&display=swap'
def gfonts(*families):
    link = GF.format('&'.join('family=' + f for f in families))
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link href="' + link + '" rel="stylesheet">')

LAYOUTS = {  # hero kind and portrait are used by the CSS in template.html
    'ring':   dict(hero='stump',  portrait='on',  theme='#133621', flat=False, fonts=(
        '<link rel="preconnect" href="https://api.fontshare.com">\n<link rel="preconnect" href="https://cdn.fontshare.com" crossorigin>\n'
        '<link href="https://api.fontshare.com/v2/css?f[]=chillax@400,500,600&display=swap" rel="stylesheet">')),
    'stripe': dict(hero='split',  portrait='off', theme='#ffffff', flat=True, fonts=gfonts('Inter:wght@300;400;500;600')),
    'wise':   dict(hero='stack',  portrait='on',  theme='#e8ebe6', flat=True, fonts=gfonts('Manrope:wght@400;500;600;800')),
    'nike':   dict(hero='cover',  portrait='on',  theme='#ffffff', flat=True, fonts=gfonts('Barlow:wght@400;500;600', 'Barlow+Condensed:wght@600;700')),
    'apple':  dict(hero='center', portrait='off', theme='#000000', flat=True, fonts=gfonts('Inter:wght@400;500;600')),
    'notion': dict(hero='center', portrait='off', theme='#ffffff', flat=True, fonts=gfonts('DM+Sans:wght@400;500;600;700')),
    'airbnb': dict(hero='splitr', portrait='on',  theme='#ffffff', flat=True, fonts=gfonts('Figtree:wght@400;500;600;700')),
    'uber':   dict(hero='split',  portrait='off', theme='#efefef', flat=True, fonts=gfonts('Inter+Tight:wght@400;500;700')),
}
AUTO_POOL = [k for k in LAYOUTS if k != 'ring']
OUT = ROOT.resolve().parent  # repo root, served by Cloudflare Pages

STOCK = {  # used only when the business has fewer than 2 photos of its own
    'review': "https://images.unsplash.com/photo-1588878309774-4b3f42a19a8f?w=900&h=1200&fit=crop&crop=entropy&auto=format&q=70",
    'work': [
        "https://images.unsplash.com/photo-1754322449185-31f56117ed87?w=800&h=800&fit=crop&crop=entropy&auto=format&q=70",
        "https://images.unsplash.com/photo-1574359173269-291f060e6fe1?w=800&h=800&fit=crop&crop=entropy&auto=format&q=70",
        "https://images.unsplash.com/photo-1521633603986-cb82a097ffba?w=800&h=800&fit=crop&crop=entropy&auto=format&q=70",
    ],
    'credit': "Stock photos from Unsplash (Richard Burlton, Scott Precious, Michael Wilson, Markus Spiske), placeholders until your own photos go in.",
}

LAW_FAQ = [
    {"tab": "Permission", "q": "Do I need permission from the council?",
     "a": "Only for trees with a Tree Preservation Order or in a conservation area. Try the checker above, and mention it when you call."},
    {"tab": "Spring", "q": "Can tree work happen in spring and summer?",
     "a": "Often, yes. Trees and hedges with active bird nests have to wait until the birds have gone, so some jobs are timed around that."},
]

def load(path):
    js = "console.log(JSON.stringify(eval(require('fs').readFileSync(process.argv[1], 'utf8'))))"
    return json.loads(subprocess.check_output(['node', '-e', js, str(path)]))

def fill(text, s):
    return text.replace('{town}', s['town']).replace('{business}', s['business']).replace('{first}', s.get('firstName') or 'us')

def defaults(s):
    first = s.get('firstName')
    d = {
        'mode': 'demo', 'rings': 12, 'yearsTrading': 0, 'insurance': '', 'quoteTime': '', 'email': '',
        'council': 'the local council', 'formKey': '', 'madeBy': 'Demo by Yegor',
        'baseLine': 'Based in {town}',
        'headings': {'services': 'What we do.', 'check': 'Can you cut it?', 'how': 'How it goes.', 'areas': 'Around {town}.', 'faq': 'Fair questions.'},
        'text': {
            'checkerIntro': "Some trees need the council's say-so first. Answer two questions and see what applies to yours.",
            'contactLine': ("Tell {first} about the job and ask for a price." if first else "Tell us about the job and ask for a price."),
            'ctaHero': 'Ask for a quote', 'ctaShort': 'Get a quote', 'ctaSubmit': ('Send to {first}' if first else 'Send'),
        },
        'quoteHeadline': (['Ask {first}', 'for a quote.'] if first else ['Ask for', 'a quote.']),
        'checker': {
            'unsureTitle': 'Worth checking first.',
            'unsure': "Your council's website lists protected trees and conservation areas. Not sure? Mention it when you call.",
            'paperwork': "Mention it when you call, so the work can be timed around the council's answer.",
            'nestingIn': 'It’s bird nesting season (roughly March to August). Work on trees with active nests has to wait.',
            'nestingOut': 'It’s outside bird nesting season, a good time for felling and heavy pruning.',
        },
        'demoNotice': 'Demo concept made by Yegor for {business}. Not the official website: built from your public Google listing and reviews, and removed on request.',
        'demoFormMsg': 'This is a demo, so nothing was sent. On the live site this goes straight to ' + ('{first}.' if first else 'the business.'),
        'title': '{business} — {town} (demo)',
        'desc': 'Demo concept for {business}, {town}.',
    }
    for k, v in d.items():
        if isinstance(v, dict):
            s[k] = {**v, **(s.get(k) or {})}
        elif k not in s or s[k] in (None, ''):
            s[k] = v
    def walk(v):
        if isinstance(v, str): return fill(v, s)
        if isinstance(v, list): return [walk(x) for x in v]
        if isinstance(v, dict): return {k: walk(x) for k, x in v.items()}
        return v
    for k in ('headings', 'text', 'checker', 'quoteHeadline', 'demoNotice', 'demoFormMsg', 'title', 'desc', 'baseLine'):
        s[k] = walk(s[k])
    tabs = {f.get('tab') for f in s.get('faq', [])}
    s['faq'] = list(s.get('faq', [])) + [f for f in LAW_FAQ if f['tab'] not in tabs]
    return s

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()

def photos(s, outdir):
    from PIL import Image, ImageOps
    if not s.get('ownerPhotos') and (s.get('photos') or {}).get('review'):
        return  # photos already set by hand
    urls = [u for u in (s.get('ownerPhotos') or []) if u][:9]
    imgs = []
    for u in urls:
        try:
            im = Image.open(io.BytesIO(fetch(u))).convert('RGB')
            if min(im.size) >= 300: imgs.append(im)
        except Exception as e:
            print('  photo skipped:', e)
    s.setdefault('photos', {})
    s['photos'].setdefault('place', '')
    wall_slots, thumbs, tiles = [], [], []
    def save(im, name, w, h):
        (outdir / 'img').mkdir(parents=True, exist_ok=True)
        ImageOps.fit(im, (w, h), method=Image.LANCZOS, centering=(0.5, 0.45)).save(outdir / 'img' / name, 'JPEG', quality=78, optimize=True, progressive=True)
        return 'img/' + name
    if len(imgs) < 2:
        s['photos']['review'] = save(imgs[0], 'review.jpg', 900, 1200) if imgs else STOCK['review']
        s['photos']['work'] = STOCK['work']
        s['photoCredits'] = (f"Large photo: {s['business']}, from their Google listing. " if imgs else '') + STOCK['credit']
        return
    # portrait-ish photo first for the tall review frame
    order = sorted(range(len(imgs)), key=lambda i: -(imgs[i].size[1] / imgs[i].size[0]))
    portrait = order[0]
    rest = [i for i in range(len(imgs)) if i != portrait]
    s['photos']['review'] = save(imgs[portrait], 'review.jpg', 900, 1200)
    plan = ['wall', 'tile1', 'wall', 'thumb1', 'tile3', 'wall', 'thumb2', 'tile5']
    services = s.get('services', [])
    work = []
    for slot, i in zip(plan, rest):
        im = imgs[i]
        if slot == 'wall':
            work.append(save(im, f'work{len(work)}.jpg', 800, 800))
        elif slot.startswith('tile'):
            k = int(slot[4:])
            if k < len(services):
                n = len(services)
                wide = k in (1, 5) or n == 4 or (n == 5 and k >= 3)
                services[k]['photo'] = save(im, f'tile{k}.jpg', 1200 if wide else 640, 760 if wide else 820)
        elif slot.startswith('thumb'):
            k = int(slot[5:])
            if k < len(s.get('reviews', [])):
                s['reviews'][k]['photo'] = save(im, f'thumb{k}.jpg', 300, 300)
    s['photos']['work'] = work
    s['photoCredits'] = f"Photos: {s['business']}, from their Google listing."

def wall_with_photos(s):
    if any('photo' in c for c in s.get('wall', [])):
        return  # layout set by hand
    facts = [c for c in s.get('wall', []) if 'photo' not in c]
    n = len(s['photos'].get('work', []))
    cells = list(facts)
    for pos, k in zip((1, 6, 8), range(n)):
        cells.insert(min(pos, len(cells)), {'photo': k})
    cells = cells[:12]
    facts_idx = [i for i, c in enumerate(cells) if 'photo' not in c]
    r = len(cells) % 4  # desktop grid is 4 wide, phone 2: fill the last row
    if r == 1 and len(facts_idx) > 4:
        cells.pop(facts_idx[-1])
    elif r in (2, 3):
        for i in facts_idx[-(4 - r):]:
            cells[i] = {**cells[i], 'wide': True}
    s['wall'] = cells

def relayout(slug, name, saved):
    """Re-render an already built demo in another layout. No network: the page's own SITE data (and its img/ files) are reused."""
    import re
    if name not in LAYOUTS: raise SystemExit(f"unknown layout {name!r}; choose from {', '.join(LAYOUTS)}")
    page_path = OUT / slug / 'index.html'
    old = page_path.read_text(encoding='utf-8')
    m = re.search(r'const SITE = (\{.*?\});\n\n/\* =+ rendering', old, re.S)
    if not m: raise SystemExit(f'{slug}: SITE block not found')
    data = m.group(1); s = json.loads(data.replace('<\\/', '</')); L = LAYOUTS[name]
    tpl = (ROOT / 'template.html').read_text(encoding='utf-8')
    page = (tpl.replace('__SITE__', data)
               .replace('__LAYOUT__', name).replace('__HERO__', L['hero']).replace('__PORTRAIT__', L['portrait'])
               .replace('__FLAT__', 'flat' if L['flat'] else '').replace('__THEME__', L['theme']).replace('__FONTS__', L['fonts'])
               .replace('__TITLE__', html.escape(s['title'])).replace('__DESC__', html.escape(s['desc'])))
    page_path.write_text(page, encoding='utf-8')
    if name != 'ring' or slug in saved: saved[slug] = name
    print('relayout', slug, name)

def saved_layouts():
    return json.loads(LAYOUT_FILE.read_text()) if LAYOUT_FILE.exists() else {}

def pick_layout(s, forced, auto, saved, towns):
    """Return the layout for this site. `towns` maps layout -> set of towns already using it (this run and saved)."""
    name = s.get('layout') or forced or saved.get(s['slug'])
    if not name and auto:
        used = [v for v in saved.values() if v in AUTO_POOL]
        def score(k):  # fewest uses overall first, never the same look twice in one town if avoidable
            return (s['town'] in towns.get(k, ()), used.count(k), AUTO_POOL.index(k))
        name = min(AUTO_POOL, key=score)
    name = name or 'ring'
    if name not in LAYOUTS:
        raise SystemExit(f"unknown layout {name!r}; choose from {', '.join(LAYOUTS)}")
    return name

def build(path, forced=None, auto=False, saved=None, towns=None):
    saved = {} if saved is None else saved
    towns = {} if towns is None else towns
    s = defaults(load(path))
    name = pick_layout(s, forced, auto, saved, towns)
    L = LAYOUTS[name]
    if name != 'ring' or s['slug'] in saved:
        saved[s['slug']] = name
    towns.setdefault(name, set()).add(s['town'])
    outdir = OUT / s['slug']
    outdir.mkdir(parents=True, exist_ok=True)
    photos(s, outdir)
    wall_with_photos(s)
    s.pop('ownerPhotos', None)
    tpl = (ROOT / 'template.html').read_text(encoding='utf-8')
    data = json.dumps(s, ensure_ascii=False, indent=2).replace('</', '<\\/')
    page = (tpl.replace('__SITE__', data)
               .replace('__LAYOUT__', name).replace('__HERO__', L['hero']).replace('__PORTRAIT__', L['portrait'])
               .replace('__FLAT__', 'flat' if L['flat'] else '').replace('__THEME__', L['theme']).replace('__FONTS__', L['fonts'])
               .replace('__TITLE__', html.escape(s['title']))
               .replace('__DESC__', html.escape(s['desc'])))
    (outdir / 'index.html').write_text(page, encoding='utf-8')
    print('built', s['slug'], name)

if __name__ == '__main__':
    args, forced, auto, paths = sys.argv[1:], None, False, []
    i = 0
    while i < len(args):
        if args[i] == '--layout': forced = args[i + 1]; i += 2
        elif args[i] == '--auto': auto = True; i += 1
        elif args[i] == '--relayout':
            saved = saved_layouts()
            for slug in args[i + 2:]: relayout(slug, args[i + 1], saved)
            LAYOUT_FILE.write_text(json.dumps(dict(sorted(saved.items())), indent=1) + '\n'); sys.exit(0)
        else: paths.append(args[i]); i += 1
    saved = saved_layouts()
    towns = {}  # layout -> towns used in this run
    for p in paths:
        build(pathlib.Path(p), forced, auto, saved, towns)
    if saved:
        LAYOUT_FILE.write_text(json.dumps(dict(sorted(saved.items())), indent=1) + '\n')
