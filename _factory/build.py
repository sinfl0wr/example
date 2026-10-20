#!/usr/bin/env python3
"""Build personal demo sites.

  python3 build.py sites/<slug>.js [...]   ->  /home/claude/example/<slug>/index.html (+ img/)

A site file is a JS object literal written by the copy agent (see RULES.md). This script adds the
standard demo texts, downloads and crops the business's own photos, and renders the template.
"""
import html, io, json, pathlib, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).parent
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

def build(path):
    s = defaults(load(path))
    outdir = OUT / s['slug']
    outdir.mkdir(parents=True, exist_ok=True)
    photos(s, outdir)
    wall_with_photos(s)
    s.pop('ownerPhotos', None)
    tpl = (ROOT / 'template.html').read_text(encoding='utf-8')
    data = json.dumps(s, ensure_ascii=False, indent=2).replace('</', '<\\/')
    page = (tpl.replace('__SITE__', data)
               .replace('__TITLE__', html.escape(s['title']))
               .replace('__DESC__', html.escape(s['desc'])))
    (outdir / 'index.html').write_text(page, encoding='utf-8')
    print('built', s['slug'])

if __name__ == '__main__':
    for p in sys.argv[1:]:
        build(pathlib.Path(p))
