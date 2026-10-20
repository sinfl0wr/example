#!/usr/bin/env python3
"""Mechanical checks on site files before building.  python3 check.py sites/*.js
Flags: risky claim words, length limits from RULES.md, map/areas mismatch, phone format."""
import json, re, subprocess, sys, pathlib

RISKY = [r'insur', r'\byears?\b', r'guarant', r'24/7', r'free (quote|estimate)', r'\bNPTC\b', r'qualif', r'certif',
         r'accredit', r'£', r'\bcheap', r'\bbest\b', r'established', r'family[- ]run', r'since \d{4}', r'\bteam of\b',
         r'same[- ]day', r'emergenc', r'\bfast\b', r'\bLantra\b', r'\bArb ?Assoc', r'\bTrustATrader\b', r'Checkatrade']
HYPE = [r'unleash', r'elevate', r'seamless', r'top-notch', r'second to none', r'world-class', r'cutting-edge']
LIMITS = {'shortName': 18, 'heroLine': 80, 'desc': 140}

def load(p):
    js = "console.log(JSON.stringify(eval(require('fs').readFileSync(process.argv[1], 'utf8'))))"
    return json.loads(subprocess.check_output(['node', '-e', js, str(p)]))

def strings(v, path=''):
    if isinstance(v, str): yield path, v
    elif isinstance(v, list):
        for i, x in enumerate(v): yield from strings(x, f'{path}[{i}]')
    elif isinstance(v, dict):
        for k, x in v.items(): yield from strings(x, f'{path}.{k}' if path else k)

def check(p):
    out = []
    try:
        s = load(p)
    except Exception as e:
        return [f'PARSE ERROR {e}']
    for k in ('slug', 'business', 'town', 'phone', 'phoneLink', 'rating', 'reviewCount', 'googleUrl', 'headline', 'heroLine'):
        if not s.get(k): out.append(f'missing {k}')
    for k in ('mode', 'photos', 'photoCredits', 'checker', 'text', 'quoteHeadline', 'demoNotice'):
        if k in s: out.append(f'should not set {k}')
    for path, t in strings({k: v for k, v in s.items() if k not in ('googleUrl', 'ownerPhotos', 'areaMap')}):
        for r in RISKY:
            if re.search(r, t, re.I): out.append(f'claim? {path}: "{t[:90]}"')
        for r in HYPE:
            if re.search(r, t, re.I): out.append(f'hype {path}: "{t[:60]}"')
        if '—' in t and path not in ('title',): out.append(f'em dash {path}')
    for k, n in LIMITS.items():
        if len(s.get(k) or '') > n: out.append(f'{k} {len(s[k])}>{n}')
    for i, h in enumerate(s.get('headline') or []):
        if len(h) > 13: out.append(f'headline[{i}] "{h}" {len(h)}>13')
    for i, x in enumerate(s.get('services') or []):
        for k, n in (('fact', 90), ('fig', 8), ('unit', 24)):
            if len(x.get(k) or '') > n: out.append(f'services[{i}].{k} {len(x[k])}>{n}')
    for i, x in enumerate(s.get('wall') or []):
        if len(str(x.get('big', ''))) > 7: out.append(f'wall[{i}].big "{x["big"]}">7')
        if len(x.get('cap', '')) > 32: out.append(f'wall[{i}].cap {len(x["cap"])}>32')
    for i, x in enumerate(s.get('reviews') or []):
        if len(x.get('text', '')) > 160: out.append(f'reviews[{i}] {len(x["text"])}>160')
    if not 3 <= len(s.get('services') or []) <= 6: out.append(f'services count {len(s.get("services") or [])}')
    areas, places = s.get('areas') or [], ((s.get('areaMap') or {}).get('places') or {})
    if set(areas) - set(places) - {s.get('town')}: out.append(f'areas not on map: {sorted(set(areas) - set(places) - {s.get("town")})}')
    c = (s.get('areaMap') or {}).get('centre')
    if c:
        for name, ll in places.items():
            d = (((ll[0] - c[0]) * 69) ** 2 + ((ll[1] - c[1]) * 43) ** 2) ** .5
            if d > 11: out.append(f'map {name} {d:.1f} mi from centre')
    if not re.fullmatch(r'0\d{4} \d{6}', s.get('phone', '')): out.append(f'phone format "{s.get("phone")}"')
    if not re.fullmatch(r'\+44\d{10}', s.get('phoneLink', '')): out.append(f'phoneLink "{s.get("phoneLink")}"')
    if len(s.get('ownerPhotos') or []) == 0: out.append('no owner photos (stock fallback)')
    return out

if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        issues = check(pathlib.Path(p))
        print(f'{pathlib.Path(p).stem}: ' + ('ok' if not issues else ''))
        for i in issues: print('   ', i)
        bad += bool(issues)
    print(f'\n{bad} file(s) with notes')
