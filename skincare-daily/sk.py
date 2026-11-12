"""Six skincare channels: one daily pipeline (Sello, 11 Nov 2026). See skincare-daily/DAILY_TASK.md.

  python3 sk.py heal    MEDIA                      # fix earlier days first: missing renders / ledger gaps -> report
  python3 sk.py planheal DATE CATALOG MEDIA        # earlier day with empty slots: keep its staged items, plan only the gaps
  python3 sk.py plan    DATE CATALOG MEDIA         # pick 36 products (fallback tiers, rolling 7-day window) -> work/DATE/plan.json
  python3 sk.py fetchjs DATE MEDIA                 # image queue -> media branch; prints one JS per chunk for the built-in browser
  python3 sk.py ingest  DATE BUNDLE [BUNDLE...]    # decode image bundles (sha256-checked) -> work/DATE/img
  python3 sk.py write   DATE                       # scripts from the listing text -> work/DATE/features.json (+ kit check)
  python3 sk.py render  DATE [slug...]             # feature.py + qa_feature.py + thumbnail/cross-day check, one retry each
  python3 sk.py stage   DATE MEDIA                 # copy renders, manifest with hashes, ledger rows for the publisher
  python3 sk.py report  DATE                       # the day's report (also lists failures)

Rules are in DAILY_TASK.md; this file only implements them. Facts come only from the dermalogica.co.za listing text.
"""
import glob, hashlib, json, os, re, shutil, subprocess, sys, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); LAUNCH = os.path.join(os.path.dirname(HERE), 'skincare-launch')
STORE = f'{LAUNCH}/store'; WORK = os.environ.get('SK_WORK', '/home/claude/skwork')
RAW = 'https://raw.githubusercontent.com/ramatladi/videosyndication/media/'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

CH = {  # domain: (handle, desk key)
    'skincare.joburg': ('@SkincareJoburgRosebank', 'moist'), 'skincare.durban': ('@SkincareDurbanWestville', 'body'),
    'dermatologist.joburg': ('@DermatologistJoburgMidrand', 'routine'), 'dermatology.joburg': ('@DermatologyJoburgBedfordview', 'labels'),
    'dermatology.durban': ('@DermatologyDurbanUmhlanga', 'hydra'), 'dermatology.capetown': ('@DermatologyCapeTown', 'sun')}
SHORT_SLOTS = ['08:00', '12:00', '16:00', '20:00']; VIDEO_SLOTS = ['10:00', '18:00']
SLUGP = {'skincare.joburg': 'rosebank', 'skincare.durban': 'westville', 'dermatologist.joburg': 'midrand',
         'dermatology.joburg': 'bedfordview', 'dermatology.durban': 'umhlanga', 'dermatology.capetown': 'capetown'}
WINDOW = 7  # rolling no-repeat window, days (per channel, per product)

# ---------------------------------------------------------------- listing text -> facts
AMERICAN = [(r'\bmoisturis(e|er|ers|ing|ed|es)\b', r'moisturiz\1'), (r'\bcolour', 'color'), (r'\bageing\b', 'aging'),
            (r'\b(minim|optim|revital|util|neutral|stabil|normal|energ|sensit|real|organ|recogn|maxim|harmon|emphas|special|personal|prior|standard|visual|mobil|oxid|immobil|synchron|categor|replen)is(e|ed|es|ing|er|ers|ation|ations)\b', r'\1iz\2'),
            (r'\bprogramme', 'program'), (r'\bcentre', 'center'), (r'\bfibre', 'fiber'), (r'\bfavour', 'favor'), (r'\bflavour', 'flavor'),
            (r'\bodour', 'odor'), (r'\bbehaviour', 'behavior'), (r'\blicence', 'license'), (r'millilitre', 'milliliter'), (r'\bgrey\b', 'gray'),
            (r'\btravelling', 'traveling'), (r'\bdefence', 'defense'), (r'\bpractise', 'practice'), (r'\bfulfil\b', 'fulfill'), (r'\bdiscolouration', 'discoloration')]


def american(s):
    for a, b in AMERICAN:
        s = re.sub(a, b, s, flags=re.I)
    return s


def clean(s):
    return re.sub(r'\s+', ' ', s.replace('​', '')).strip(' .;,-–')


def split_list(s):
    s = clean(s)
    if '•' in s:
        return [clean(x) for x in s.split('•') if clean(x)]
    starts = r'(?:[A-Z][a-z\-]+(?:s|es)|Gentle|Visibly|Non-comedogenic|Portable|Ideal|Suitable|Lightweight|Shimmering|SPF\d+|Instantly|Immediately|Long-lasting|Clinically|Formulated|Fragrance-free|Dermatologist|Safe|Perfect|Great|Easy|Brighter|Smoother|Clearer|Firmer|Softer|Deeply|Clear|Improved|Reduced)\b'
    parts = re.split(r'(?<=[a-z0-9%)])\s+(?=' + starts + ')', s)
    return [clean(p) for p in parts if clean(p)]


def sentences(s):
    return [clean(x) + '.' for x in re.split(r'(?<=[.!?])\s+(?=[A-Z])', clean(s)) if len(clean(x)) > 3]


def parse(p):
    """Facts from one catalog entry. Every string here is the store's own text (American spelling applied later)."""
    t, body = p.get('text', ''), p.get('body', '')
    i = t.find('View full details'); s = t[i + 17:] if i >= 0 else ''
    m = re.search(r'\bbenefits (.*?) how to use (.*?)(?: ingredients | frequently asked|$)', s, re.S | re.I)
    ben, how = (m.group(1), m.group(2)) if m else ('', '')
    if not how:
        mh = re.search(r'how to use (.*?)(?: ingredients | frequently asked|$)', s, re.I); how = mh.group(1) if mh else ''
    tl = re.search(re.escape(p['title']) + r'\s+' + re.escape(p['title']) + r'\s+(.*?)\s+(?:\d[\d,]* reviews?|No reviews|Regular price)', t, re.I)
    tagline = clean(tl.group(1)) if tl else ''
    rec = re.search(r'recommended for:\s*(.*?)(?:\s+[A-Z][a-z].{20,}?\.)', body)
    inside = []
    mi = re.search(r"(?:what'?s inside|kit includes|contains|includes)\s*:?\s*(.*?)(?:skin concerns:|skip to product|$)", body + ' ', re.I | re.S)
    if mi:
        tok = r"(?:[A-Z][\w\-+'.]*|SPF\s?\d+|\d+[\w.]*|\+|&)"
        for name, size in re.findall(r"(" + tok + r"(?:\s+(?:" + tok + r"|and|of|for|with))*)\s*\(\s*([\d.,]+\s*(?:ml|g|oz)\b)[^)]*\)", mi.group(1)):
            inside.append({'name': clean(name), 'size': clean(size).replace(' ', '').lower()})
        if not inside:  # "name 50ml + name 75ml" / "Name 1.7 oz (desc)"
            for name, size in re.findall(r"([A-Za-z][\w\-+' ]{2,50}?)\s+([\d.]+\s?(?:ml|g|oz))\b", mi.group(1)):
                inside.append({'name': clean(re.sub(r'^(and|\+|,)\s*', '', name.split(')')[-1].split(',')[-1].strip())), 'size': clean(size).replace(' ', '').lower()})
        if not inside:  # all-lowercase listings
            for name, size in re.findall(r"([a-z][a-z0-9+\-' ]{2,40}?)\s*\(\s*([\d.,]+\s*(?:ml|g))\s*\)", mi.group(1), re.I):
                inside.append({'name': clean(name), 'size': clean(size).replace(' ', '').lower()})
    desc = body
    for cut in ("What's inside", 'This kit helps', 'about the kit', 'Skin concerns:', 'recommended for:'):
        k = desc.lower().find(cut.lower())
        if k > 0: desc = desc[:k]
    if desc.lower().startswith('recommended for'):
        desc = re.sub(r'^recommended for:.*?(?=[A-Z][a-z]+ [a-z])', '', desc)
    helps = re.search(r'This kit helps to:?\s*(.*?)(?:about the kit|what\'?s inside|$)', body, re.I)
    desc = re.sub(r'(?i)^\s*recommended (?:for|to address)[^:]*:.*?(?=\b[A-Z][\w\-]+(?: [A-Za-z\-²,]+){4,})', '', desc)
    bl = split_list(ben) or split_list(helps.group(1) if helps else '')
    bl = [re.sub(r'^(?:[A-Z][\w\-]*(?: [\w\-+]+){0,5}):\s*', '', re.sub(r'\s+[A-Z][\w\-]*(?: [\w\-+]+){0,5}:$', '', b)) for b in bl]
    bl = [b for b in bl if b and not b.endswith(':') and len(b) > 8]
    return {'tagline': tagline, 'description': sentences(desc)[:4], 'benefits': bl[:6],
            'how': sentences(how)[:5], 'inside': inside, 'recommended': clean(rec.group(1)) if rec else '',
            'kit': bool(inside) or bool(re.search(r'\b(kit|set|duo|trio|system|pair)\b', p['title'], re.I))}


def cats(p):
    return [x[9:] for x in p.get('tags', []) if x.startswith('category:')]


EXCLUDE = re.compile(r'sample|gwp|gift|scrunchie|gua sha|free |headband|mixing bowl', re.I)


def eligible(p):
    return 'variants' in p and p.get('type') not in ('Treatment', 'Free Product', 'Professional Product') and not EXCLUDE.search(p['title']) \
        and 'samples' not in cats(p) and any(v['sku'] and v['available'] for v in p['variants']) and len(p.get('images', [])) >= 2 \
        and not (parse(p)['kit'] and not parse(p)['inside'])  # a kit whose listing doesn't name its contents can't be described accurately


def desk_fit(p, desk):
    """1 = the channel's own desk, 2 = face product the desk can cover from its angle (tier c), 0 = no.
    Uses only this product's own listing text (the page also carries store-wide offers, which must not count)."""
    t = p['title'].lower(); c = set(cats(p)); f = parse(p)
    own = ' '.join(f['description'] + f['benefits'] + f['how'] + [f['tagline']]).lower()
    body = 'body' in t or 'body' in c; spf = 'spf' in t or 'spf' in c
    if desk == 'body':
        return 1 if body else (2 if re.search(r'\bneck\b|d[ée]collet|chest', ' '.join(f['how']).lower()) and not spf else 0)
    cleanser = bool(re.search(r'cleans|wash|precleanse|foliant|peel|patch|mask|masque', t))
    if desk == 'sun':
        return 1 if spf else (2 if not cleanser and re.search(r'\buv\b|sun exposure|daytime|free radical|environmental|pollution|photo-?ag|antioxidant', own) else 0)
    if body:
        return 0
    if spf:
        return 2 if desk == 'routine' or (desk == 'moist' and 'moistur' in own) else 0  # sunscreens belong to Cape Town first
    if desk == 'moist':
        if (c & {'moisturisers', 'masques'} or re.search(r'cream|moistur|jelly|lotion|masque|balm|water gel|calm water', t)) and not re.search(r'cleans|wash', t): return 1
        return 2 if not cleanser and re.search(r'serum|oil|eye|mist|booster|treatment', t) else 0
    if desk == 'routine':
        return 1 if c & {'cleansers', 'exfoliants', 'toners', 'skin_kits_and_sets'} or f['inside'] or re.search(r'kit|set|duo|system|cleans|wash|exfoli|foliant|toner|steps', t) else 2
    if desk == 'labels':
        return 1 if c & {'facial_oils_and_serums', 'concentrated_boosters', 'targeted_treatments', 'innovations'} or re.search(r'serum|booster|peel|treatment|patch', t) else 2
    if desk == 'hydra':
        if c & {'toners', 'eye_treatments', 'concentrated_boosters'} or re.search(r'mist|hydrat|toner|oil\b|booster|eye|water|jelly', t): return 1
        return 2 if 'hydrat' in own or 'moisture' in own else 0
    return 0


# ---------------------------------------------------------------- history (media branch manifests)
def history(media):
    rows = []
    for f in sorted(glob.glob(f'{media}/skincare-daily/*/manifest.json')) + [f'{media}/skincare-launch/v2.1/manifest.json']:
        if not os.path.exists(f): continue
        for it in json.load(open(f))['items']:
            name = it['product']['name'] if isinstance(it['product'], dict) else it['product']
            day = (it.get('slot_sast') or '2026-11-07')[:10] if 'v2.1' not in f else '2026-11-07'
            rows.append({'date': day, 'domain': it['domain'], 'sku': it.get('sku'), 'product': clean(name).lower(), 'title': it.get('title', ''),
                         'thumb': f"{media}/{it['thumbnail_path']}" if it.get('thumbnail_path') else None})
    staged = {r['date'] for r in rows}
    for f in sorted(glob.glob(f'{WORK}/*/plan.json')):  # planned but not yet staged days count too
        pl = json.load(open(f))
        if pl['date'] in staged: continue
        rows += [{'date': pl['date'], 'domain': i['domain'], 'sku': i['sku'], 'product': clean(i['title']).lower(), 'title': '', 'thumb': None} for i in pl['items']]
    return rows


# ---------------------------------------------------------------- plan with fallback tiers
def plan(date, catalog, media, fixed=None, banned=None):
    """fixed: picks to keep as they are (replanning only some slots); banned: {(domain, slot): {sku or product name}}."""
    fixed = fixed or []; banned = banned or {}
    D = dt.date.fromisoformat(date); P = [p for p in json.load(open(catalog))['products'] if eligible(p)]
    H = [h for h in history(media) if h['date'] < date]
    since = lambda h: (D - dt.date.fromisoformat(h['date'])).days
    last_any = {}; last_ch = {}; sku_used = {}
    for h in H:
        last_any[h['product']] = min(last_any.get(h['product'], 99), since(h))
        last_ch[(h['domain'], h['product'])] = min(last_ch.get((h['domain'], h['product']), 99), since(h))
        if h['sku']: sku_used[h['sku']] = min(sku_used.get(h['sku'], 99), since(h))
    today, picks, log = {clean(f['title']).lower() for f in fixed}, list(fixed), []
    taken = {(f['domain'], f['slot']) for f in fixed}
    order = ['dermatology.capetown', 'skincare.durban', 'skincare.joburg', 'dermatologist.joburg', 'dermatology.joburg', 'dermatology.durban']  # thinnest desks first
    slots = [(d, s, 'short') for d in order for s in SHORT_SLOTS] + [(d, s, 'video') for d in order for s in VIDEO_SLOTS]
    slots.sort(key=lambda x: (x[1] != '08:00', order.index(x[0]), x[1]))  # 08:00 Shorts first
    for dom, slot, fmt in slots:
        if (dom, slot) in taken: continue
        desk = CH[dom][1]; best = None
        for p in P:
            name = clean(p['title']).lower()
            if name in today or last_ch.get((dom, name), 99) < WINDOW: continue
            fit = desk_fit(p, desk)
            if not fit: continue
            for v in p['variants']:
                if not (v['sku'] and v['available']): continue
                fresh_prod = last_any.get(name, 99) >= WINDOW; fresh_sku = sku_used.get(v['sku'], 99) >= WINDOW
                if fit == 1 and fresh_prod and fresh_sku: tier = 'a'
                elif fit == 1 and fresh_sku: tier = 'b'
                elif fit == 2 and fresh_prod: tier = 'c'
                else: tier = 'd'
                bn = set(banned.get((dom, slot), ())) | set(banned.get(('*', '*'), ()))
                if v['sku'] in bn or name in bn: continue
                score = ('abcd'.index(tier), fit, -min(last_any.get(name, 99), 99), -min(last_ch.get((dom, name), 99), 99), -min(sku_used.get(v['sku'], 99), 99),
                         0 if (fmt == 'video') == (len(p['images']) >= 5) else 1, p['handle'], v['sku'])
                if best is None or score < best[0]: best = (score, p, v, tier)
        if best is None:
            log.append({'domain': dom, 'slot': slot, 'format': fmt, 'tier': None, 'reason': 'no product at all (catalog empty?)'}); continue
        _, p, v, tier = best; today.add(clean(p['title']).lower())
        why = {'a': 'unused SKU in the desk (7-day window)', 'b': 'different size/kit of a desk product, SKU never used before',
               'c': f'face product covered from the {desk} angle', 'd': 'least recently used product (catalog thin; new script and visuals)'}[tier]
        picks.append({'domain': dom, 'slot': slot, 'format': fmt, 'handle': p['handle'], 'title': p['title'], 'sku': v['sku'],
                      'variant': v['title'], 'variant_id': v['id'], 'tier': tier, 'why': why,
                      'last_used_days_ago': None if last_any.get(clean(p['title']).lower(), 99) == 99 else last_any[clean(p['title']).lower()]})
        log.append({k: picks[-1][k] for k in ('domain', 'slot', 'format', 'title', 'sku', 'tier', 'why')})
    os.makedirs(f'{WORK}/{date}', exist_ok=True)
    json.dump({'date': date, 'catalog': os.path.abspath(catalog), 'window_days': WINDOW, 'items': picks}, open(f'{WORK}/{date}/plan.json', 'w'), indent=1)
    from collections import Counter
    print(json.dumps({'items': len(picks), 'tiers': Counter(p['tier'] for p in picks)}, default=str))
    return picks


def planheal(date, catalog, media):
    """Heal an earlier day: keep its staged items as they are (existing) and plan only the empty slots."""
    m = json.load(open(f'{media}/skincare-daily/{date}/manifest.json'))
    fixed = [{'domain': it['domain'], 'slot': it['slot_sast'][11:16], 'format': it['format'], 'title': it['product']['name'], 'sku': it['sku'],
              'handle': None, 'tier': it.get('selection', {}).get('tier'), 'why': 'already staged', 'existing': True} for it in m['items']]
    return plan(date, catalog, media, fixed=fixed)


def replan(date, media):
    """Slots that `write` could not fill (kit/text/overlap problems) get the next product; everything else stays."""
    w = f'{WORK}/{date}'; pl = json.load(open(f'{w}/plan.json')); probs = json.load(open(f'{w}/write_problems.json'))
    probs = [p for p in probs if 'fewer than 2 store images' not in p['problem']]  # missing images: run fetchjs again, don't ban the product
    if not probs: return 0
    bad = {(p['item']['domain'], p['item']['slot']) for p in probs}
    ban = json.load(open(f'{w}/banned.json')) if os.path.exists(f'{w}/banned.json') else {}
    for p in probs:  # script overlap and kit problems belong to the product, not the slot: ban it for every slot of the day
        key = '*|*' if re.search(r'overlap|kit', p['problem']) else f"{p['item']['domain']}|{p['item']['slot']}"
        ban.setdefault(key, []).extend([p['item']['sku'], clean(p['item']['title']).lower()])
    json.dump(ban, open(f'{w}/banned.json', 'w'), indent=1)
    plan(date, pl['catalog'], media, fixed=[i for i in pl['items'] if (i['domain'], i['slot']) not in bad],
         banned={tuple(k.split('|')): set(v) for k, v in ban.items()})
    return len(bad)


# ---------------------------------------------------------------- images via the built-in browser
def image_list(p, sku):
    """Packshot first (the variant's own image), then listing images minus badges/reviews."""
    v = [x for x in p['variants'] if x['sku'] == sku][0]; vid = v['id']
    imgs = [i for i in p['images'] if not re.search(r'award|badge|review|quote|testimonial|size.?chart|gwp|gift', i['src'], re.I)]
    pack = v.get('img') or next((i['src'] for i in imgs if vid in (i.get('variant_ids') or [])), None) or imgs[0]['src']
    pack = pack if pack.startswith('http') else 'https:' + pack
    rest = []
    for i in imgs:
        u = i['src'] if i['src'].startswith('http') else 'https:' + i['src']
        if u.split('?')[0] != pack.split('?')[0] and (i.get('w') or 1000) >= 600 and not (i.get('variant_ids') and vid not in i['variant_ids']):
            rest.append(u)
    return [pack] + rest[:9]


def fetchjs(date, media, per=12):
    """Write the image queue to the media branch (raw GitHub allows cross-origin reads) and return one short JS per chunk."""
    pl = json.load(open(f'{WORK}/{date}/plan.json')); cat = {p['handle']: p for p in json.load(open(pl['catalog']))['products']}
    have = json.load(open(f'{WORK}/{date}/images.json')) if os.path.exists(f'{WORK}/{date}/images.json') else {}
    q = {it['sku']: image_list(cat[it['handle']], it['sku']) for it in pl['items'] if it['sku'] not in have and not it.get('existing')}  # only what's missing
    keys = list(q); d = f'{media}/skincare-daily/{date}/fetch'; os.makedirs(d, exist_ok=True); js = []
    tag = '' if not have else f'-{len(glob.glob(f"{d}/queue-*.json"))}'
    for n in range(0, len(keys), per):
        qn = f'queue{tag}-{n // per}.json'
        json.dump({k: q[k] for k in keys[n:n + per]}, open(f'{d}/{qn}', 'w'), indent=0)
        js.append(JS.replace('QURL', f"{RAW}skincare-daily/{date}/fetch/{qn}?t=' + Date.now() + '").replace('NAME', f'sk-{date}{tag}-{n // per}.json'))
    return js


JS = ("const W=await fetch('QURL').then(r=>r.json());const out={};for(const[s,L]of Object.entries(W)){out[s]=[];for(const u of L){try{"
      "const f=u+(u.includes('?')?'&':'?')+'width=1400';const b=await(await fetch(f)).arrayBuffer();"
      "const h=[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(x=>x.toString(16).padStart(2,'0')).join('');"
      "let t='';const a=new Uint8Array(b);for(let i=0;i<a.length;i+=32768)t+=String.fromCharCode.apply(null,a.subarray(i,i+32768));"
      "out[s].push({url:u,sha256:h,b64:btoa(t)})}catch(e){out[s].push({url:u,error:String(e)})}}}"
      "const bl=new Blob([JSON.stringify(out)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(bl);"
      "a.download='NAME';document.body.appendChild(a);a.click();a.remove();Object.keys(out).length+' products, '+bl.size+' bytes'")


def ingest(date, bundles):
    import base64, io
    from PIL import Image
    d = f'{WORK}/{date}/img'; os.makedirs(d, exist_ok=True); idx = f'{WORK}/{date}/images.json'
    man = json.load(open(idx)) if os.path.exists(idx) else {}
    tag = 'd' + date[5:7] + date[8:10]
    for b in bundles:
        for sku, L in json.load(open(b)).items():
            if sku in man and man[sku]: continue
            man[sku] = []
            for k, x in enumerate(L):
                if 'b64' not in x: continue
                raw = base64.b64decode(x['b64'])
                if hashlib.sha256(raw).hexdigest() != x['sha256']: raise SystemExit(f'hash mismatch {sku} {k}')
                im = Image.open(io.BytesIO(raw)); fmt = im.format.lower(); ext = 'png' if fmt in ('png', 'webp') else 'jpg'
                fn = f'{tag}-{sku}-{len(man[sku]):02d}.{ext}'
                if fmt == 'webp': im.save(f'{d}/{fn}')
                else: open(f'{d}/{fn}', 'wb').write(raw)
                man[sku].append({'file': fn, 'url': x['url'], 'sha256': x['sha256'], 'size': im.size})
    json.dump(man, open(idx, 'w'), indent=1); print({k: len(v) for k, v in man.items()})


# ---------------------------------------------------------------- writing (all facts from the listing)
SMALL = {'spf50': 'SPF50', 'spf30': 'SPF30', 'spf40': 'SPF40', 'spf': 'SPF', 'biolumin-c': 'BioLumin-C', 'powerbright': 'PowerBright',
         'ultracalming': 'UltraCalming', 'multivitamin': 'MultiVitamin', 'skinperfect': 'SkinPerfect', 'porescreen': 'PoreScreen',
         'neurotouch': 'NeuroTouch', 'ml': 'mL', 'g': 'g', '+': '+', 'and': 'and', 'of': 'of', 'for': 'for', 'to': 'to', 'with': 'with', 'the': 'the'}
NUMW = {'15': 'fifteen', '20': 'twenty', '25': 'twenty-five', '30': 'thirty', '40': 'forty', '45': 'forty-five', '50': 'fifty', '60': 'sixty', '100': 'one hundred'}


def tcase(name):
    out = []
    for i, w in enumerate(name.split()):
        lw = w.lower()
        if lw in SMALL and (i or lw not in ('and', 'of', 'for', 'to', 'with', 'the')): out.append(SMALL[lw])
        elif lw.startswith('(') or re.match(r'^\d', lw): out.append(w)
        else: out.append('-'.join(x[:1].upper() + x[1:] for x in w.split('-')))
    return ' '.join(out)


def spoken(name):
    s = re.sub(r'\s*\(.*?\)\s*', ' ', name).replace('+', 'plus').replace('&', 'and')
    s = re.sub(r'(?i)\bspf\s?(\d+)', lambda m: 'SPF ' + NUMW.get(m.group(1), m.group(1)), s)
    s = re.sub(r'(?i)\b(\d+)\s?ml\b', lambda m: NUMW.get(m.group(1), m.group(1)) + ' milliliters', s)
    return clean(s)


def say_units(s):
    s = re.sub(r'(?i)\bspf\s?(\d+)', lambda m: 'SPF ' + NUMW.get(m.group(1), m.group(1)), s)
    s = re.sub(r'(\d+)\s?ml\b', lambda m: NUMW.get(m.group(1), m.group(1)) + ' milliliters', s, flags=re.I)
    s = re.sub(r'(\d+)\s?g\b', lambda m: NUMW.get(m.group(1), m.group(1)) + ' grams', s)
    return s.replace('%', ' percent').replace('&', 'and').replace('+', 'plus')


STOP = {'on', 'to', 'the', 'and', 'of', 'with', 'into', 'for', 'a', 'an', 'in', 'or', 'your', 'from', 'over', 'onto', 'at', 'by', 'then', 'while', 'that'}


def short_head(s, n=46):
    s = clean(american(s)).rstrip('.')
    s = re.sub(r'^[A-Z][\w\s+\-]{2,40}:\s*', '', s) or s  # "Product name: direction" -> direction
    if len(s) > n:
        for sep in (', ', ' and ', ' – ', ' - ', '; '):
            head = s.split(sep)[0]
            if 8 <= len(head) <= n: s = head; break
    if len(s) > n:
        full = s.split(' '); w = s[:n + 1].split(' ')[:-1]
        while w and len(w) < len(full) and w[-1][:1].isupper() and full[len(w)][:1].isupper(): w.pop()  # don't split a name
        while w and w[-1].lower().strip(',') in STOP: w.pop()
        s = ' '.join(w).rstrip(',;:')
    return s[:1].upper() + s[1:]


SMALLW = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'with', 'vs', 'via', 'into', 'over'}


def smart_title(s):
    w = s.split(' ')
    return ' '.join((x if (i and x.lower() in SMALLW) else (x[:1].upper() + x[1:])) if not re.match(r'^[A-Z]{2,}', x) else x for i, x in enumerate(w)).replace(' And ', ' and ')


def words(n, *texts):
    out, c = [], 0
    for t in texts:
        k = len(t.split())
        if c + k > n and out: break
        out.append(t); c += k
    return ' '.join(out)


ANGLE = {'moist': ('Rosebank', 'moisturizer and texture desk'), 'body': ('Westville', 'body care desk'), 'routine': ('Midrand', 'routine desk'),
         'labels': ('Bedfordview', 'labels and ingredients desk'), 'hydra': ('uMhlanga', 'hydration and layering desk'), 'sun': ('Cape Town', 'daily sun care desk')}
TIER_C_LINE = {'body': 'Body care reaches the neck, and the directions for this one go there too.',
               'sun': 'Sun care runs all day, so today it is a product that sits next to your SPF.',
               'moist': 'Today, a product that sits next to your moisturizer.', 'routine': 'Today, where this one sits in a routine.',
               'labels': 'Today, a close read of this listing.', 'hydra': 'Today, how this one layers.'}
SHORT_TITLES = ['Dermalogica {N}: {T} #shorts', 'How to Use Dermalogica {N} #shorts', 'Dermalogica {N} in Under a Minute: {T} #shorts',
                '{A}: Dermalogica {N} #shorts', 'Dermalogica {N}, Explained Fast #shorts', 'What Dermalogica {N} Does: {T} #shorts']
VIDEO_TITLES = ['Dermalogica {N} Review: {T}, How to Use It', 'Dermalogica {N}: What It Does and How to Use It', 'Dermalogica {N}, Explained', 'Dermalogica {N}: How to Use It',
                'Dermalogica {N} Explained: {T}', '{A}: Dermalogica {N}, Step by Step', 'Dermalogica {N}: Benefits, Directions and Who It Suits']
DESK_TITLE = {'moist': 'Moisturizer Desk', 'body': 'Body Care', 'routine': 'Routine Builder', 'labels': 'Label Read', 'hydra': 'Layering Guide', 'sun': 'Daily SPF'}


NOPE = re.compile(r'(?i)(?:[_\-]b_?a\d?[_.\-]|before|after|clinical|claim|number.?of.?uses|\.gif|consumer|survey|award|review)')


THUMB_FALLBACK = {'moist': 'Texture check', 'body': 'Body care pick', 'routine': 'Where it fits', 'labels': 'Label read', 'hydra': 'How to layer it', 'sun': 'Daily sun care pick'}


def thumb_text(tag, ben):
    c = []
    for t in [tag] + ben[:2]:
        t = clean(american(t or '')).rstrip('.')
        c += [t, re.split(r',| and | \+ | – ', t)[0]]
    for t in c:
        if 6 <= len(t) <= 30 and len(t.split()) >= 2 and t.split()[-1].lower() not in STOP: return t[:1].upper() + t[1:]
    return None


def kit_check(f, item):
    """Kit components and sizes must come from the kit's own listing ("What's inside") and appear in facts and narration."""
    errs = []
    for c in f['inside']:
        nm, sz = c['name'].lower(), c['size'].lower()
        blob_f = ' '.join(item['facts']).lower(); blob_s = ' '.join(s['say'] for s in item['scenes']).lower()
        if nm not in blob_f or sz not in blob_f.replace(' ', ''): errs.append(f'facts miss {c}')
        if spoken(c['name']).lower() not in blob_s: errs.append(f'narration misses {c["name"]}')
    if f['kit'] and not f['inside']:
        errs.append("kit listing has no parsable \"What's inside\" (components not verified)")
    return errs


def prior_scripts(media, date):
    """Narration and image URLs of every earlier item, by product name (for no-repeat scripts and visuals)."""
    says, urls = {}, {}
    files = glob.glob(f'{media}/skincare-daily/*/features*.json') + glob.glob(f'{WORK}/*/features.json') + [f'{LAUNCH}/features.json']
    for f in files:
        d = os.path.basename(os.path.dirname(f)) if 'skincare-launch' not in f else '2026-11-07'
        if d >= date: continue
        try: vids = json.load(open(f)).get('videos', [])
        except Exception: continue
        for v in vids:
            says.setdefault(clean(v['product_name']).lower(), []).append(' '.join(s['say'] for s in v['scenes']))
    for f in glob.glob(f'{media}/skincare-daily/*/images/sources.json'):
        if os.path.basename(os.path.dirname(os.path.dirname(f))) >= date: continue
        for x in json.load(open(f)): urls.setdefault(x.get('sku'), set()).add(x['source'].split('?')[0])
    return says, urls


COMMON = set('''that this with your from into over then after before apply skin face neck dermalogica link description store
listing product products desk today care daily which helps help more less while also onto using use used each about their there
milliliters grams fifty thirty fifteen twenty sentence morning night evening twice once day days time minute minutes
rosebank westville midrand bedfordview umhlanga cape town moisturizer texture body routine labels ingredients hydration
layering doctors dermatologists general information first dermatology capetown durban joburg isn't'''.split())


def overlap(a, b, name=''):
    """Share of distinctive words (not the product name, not stock skincare words) that two scripts have in common."""
    drop = COMMON | set(re.findall(r'[a-z]{4,}', name.lower()))
    A = {w for w in re.findall(r'[a-z]{4,}', a.lower())} - drop; B = {w for w in re.findall(r'[a-z]{4,}', b.lower())} - drop
    return len(A & B) / max(1, min(len(A), len(B)))


def rot(L, k):
    return L[k % len(L):] + L[:k % len(L)] if L else L


def write(date):
    pl = json.load(open(f'{WORK}/{date}/plan.json')); cat = {p['handle']: p for p in json.load(open(pl['catalog']))['products']}
    imgs = json.load(open(f'{WORK}/{date}/images.json')); H = history(os.environ.get('SK_MEDIA', '/tmp/launch-media'))
    used_titles = {h['title'].lower() for h in H}; base = json.load(open(f'{LAUNCH}/features.json'))
    prev_says, prev_urls = prior_scripts(os.environ.get('SK_MEDIA', '/tmp/launch-media'), date)
    vids, problems, k = [], [], 0
    for n, it in enumerate(pl['items']):
        if it.get('existing'): continue  # heal: already staged on that day
        p = cat[it['handle']]; f = parse(p); desk = CH[it['domain']][1]; loc, deskname = ANGLE[desk]; short = it['format'] == 'short'
        name = clean(p['title']); N = tcase(name); sp = spoken(name)
        L = imgs.get(it['sku'], [])
        if len(L) < 2: problems.append((it, 'fewer than 2 store images')); continue
        for x in L: shutil.copy(f"{WORK}/{date}/img/{x['file']}", f"{STORE}/{x['file']}")
        skip = json.load(open(f'{WORK}/{date}/skip.json')) if os.path.exists(f'{WORK}/{date}/skip.json') else []
        ok = [x for x in L[1:] if not NOPE.search(x['url']) and x['file'] not in skip]
        seen = set().union(*[u for s_, u in prev_urls.items() if s_ and any(s_ == y['sku'] for y in pl['items'] if y['title'] == p['title'])] or [set()]) | prev_urls.get(it['sku'], set())
        pics = [x['file'] for x in ok if x['url'].split('?')[0] not in seen] + [x['file'] for x in ok if x['url'].split('?')[0] in seen] or [L[0]['file']]
        kprev = len(prev_says.get(clean(p['title']).lower(), []))
        pic = lambda i: pics[i % len(pics)]
        tag = american(f['tagline']) or (american(f['benefits'][0]) if f['benefits'] else 'how to use it')
        T = smart_title(short_head(tag, 44)) if tag else 'How to Use It'
        said = ' '.join(prev_says.get(clean(p['title']).lower(), [])).lower()
        fresh_first = lambda L: [x for x in L if say_units(x).lower().rstrip('.')[:60] not in said] + [x for x in L if say_units(x).lower().rstrip('.')[:60] in said]
        desc = fresh_first(rot([american(x) for x in f['description']], kprev)); ben = fresh_first(rot([american(x) for x in f['benefits']], kprev)); how = [american(x) for x in f['how']]
        n_fresh_ben = sum(1 for x in ben if say_units(x).lower().rstrip('.')[:60] not in said)
        size = it['variant'] if re.match(r'^[\d.]+\s?(?:ml|g|oz)\b', it['variant'] or '', re.I) else ''
        size_in_name = bool(size) and re.sub(r'\s', '', size.lower()) in re.sub(r'\s', '', name.lower())
        intro = f"{loc} {deskname}: Dermalogica {sp}" + (f", {say_units(size)}" if size and not size_in_name else '') + '.'
        if it['tier'] == 'c': intro += ' ' + TIER_C_LINE[desk]
        sc = [dict(type='cover', sub=(size.replace('ml', ' mL') + ' · ' if size else '') + short_head(tag, 40), say=intro)]
        if f['inside']:
            parts = [f"{say_units(c['name'])}, {say_units(c['size'])}" for c in f['inside']]
            sc.append(dict(type='bullets', kicker="WHAT'S INSIDE", headline=f"{len(f['inside'])} products in one kit",
                           items=[f"{tcase(c['name'])} ({c['size'].replace('ml', ' mL')})" for c in f['inside']][:4],
                           say='Inside the kit: ' + '; '.join(parts) + '.'))
        if desc:
            sc.append(dict(type='figure', image=pic(0), kicker='WHAT IT IS', headline=short_head(tag or desc[0]), say=say_units(words(34 if short else 95, *desc))))
        bl = ben[:2] if short else ben[:max(2, min(4, n_fresh_ben)) if kprev else 4]
        if bl:
            if short:
                sc.append(dict(type='figure', image=pic(1), kicker='BENEFITS', headline=short_head(bl[0]), say=say_units('It ' + bl[0][0].lower() + bl[0][1:] + (', and ' + bl[1][0].lower() + bl[1][1:] if len(bl) > 1 else '') + '.')))
            else:
                for j, b in enumerate(bl):
                    sc.append(dict(type='figure', image=pic(1 + j), kicker=f'BENEFIT {j + 1}', headline=short_head(b, 52), say=say_units(b + '.')))
        if f['recommended'] and not short:
            sc.append(dict(type='note', kicker='RECOMMENDED FOR', headline=short_head(american(f['recommended']), 70), say=say_units('The listing recommends it for ' + american(f['recommended']).rstrip('.') + '.')))
        if how:
            items = []
            for h in how:
                h = re.sub(r'^[A-Za-z][\w\-+ ]{2,50}:\s*', '', h)  # "product: direction"
                h = re.sub(r'^(?:after|following|for best results|for added benefits|once|before|in the|morning and night|then|and)\b[^,]*,\s*', '', h, flags=re.I)
                h = short_head(h, 40)
                if len(h) >= 10 and not re.fullmatch(r'[\d\W]+', h) and h not in items: items.append(h)
            items = items[:3] or [short_head(how[0], 40)]
            sc.append(dict(type='steps', kicker='HOW TO USE', headline=short_head(how[0], 40) if len(how) == 1 else 'Directions from the listing', items=items,
                           say=say_units(words(30 if short else 95, *how))))
        if not short and it['domain'] != 'skincare.joburg' and CH[it['domain']][1] in ('routine', 'labels', 'hydra', 'sun') and base['channels'][it['domain']]['credential_line']:
            sc.insert(1, dict(type='note', image=pic(2), kicker='FIRST', headline='Not dermatologists or doctors. General product information.',
                              say=f"First, {it['domain'].replace('.', ' dot ')} isn't run by dermatologists or doctors. This is general product information from the store listing."))
        if not short:
            extra = [x for x in pics if x not in {s.get('image') for s in sc}]
            for j, x in enumerate(extra[:2]):
                b = (ben[4 + j] if len(ben) > 4 + j else None)
                if b: sc.insert(-1, dict(type='figure', image=x, kicker='ALSO', headline=short_head(b, 52), say=say_units(b + '.')))
        if short:  # keep Shorts under a minute: drop the description scene first, then the benefits scene
            for kick in ('WHAT IT IS', 'BENEFITS'):
                if sum(len(x['say']) for x in sc) + 80 > 560:  # characters read more reliably than words (acronyms, numbers)
                    sc = [x for x in sc if x.get('kicker') != kick]
        sc.append(dict(type='end', sub=(size.replace('ml', ' mL') if size else N), say=f"That's Dermalogica {sp}. The link is in the description."))
        # titles: first unused template
        pool = SHORT_TITLES if short else VIDEO_TITLES; title = None
        for j in range(len(pool)):
            cand = pool[(n + j) % len(pool)].format(N=N + (f' {size.replace("ml", " mL")}' if size and it['tier'] in 'bd' and not size_in_name else ''), T=T, A=DESK_TITLE[desk])
            if len(cand) <= 100 and cand.lower() not in used_titles and name.lower() in cand.lower(): title = cand; break
        if not title:
            title = (f'Dermalogica {N}: {DESK_TITLE[desk]} {date[5:]}' + (' #shorts' if short else ''))[:100]
        used_titles.add(title.lower())
        facts = ([short_head(tag, 120)] if tag else []) + ([f"What's inside: " + '; '.join(f"{c['name']} ({c['size']})" for c in f['inside'])] if f['inside'] else []) \
            + [b for b in ben[:4]] + ([('How to use: ' + ' '.join(how))[:300]] if how else [])
        item = dict(slug=f"{SLUGP[it['domain']]}-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}" + (f"-{re.sub(r'[^a-z0-9]+', '', size.lower())}" if it['tier'] in 'bd' and size else '') + ('-short' if short else ''),
                    domain=it['domain'], format='short' if short else 'video', product_name=name, spoken_name=sp,
                    product_url=f"https://dermalogica.co.za/products/{it['handle']}?variant={it['variant_id']}", packshot=L[0]['file'],
                    title=title, lead=f"Dermalogica {name}: {american(tag)}, from the {loc} {deskname}.", facts=[american(x) for x in facts],
                    tags=[name, f'dermalogica {name}', ANGLE[desk][1].replace(' desk', ''), loc.lower() + ' skincare', 'dermalogica south africa'],
                    hashtags=f"#Dermalogica #{re.sub(r'[^A-Za-z0-9]', '', american(N))} #{re.sub(r'[^A-Za-z]', '', DESK_TITLE[desk])}" + (' #shorts' if short else ''),
                    thumb=dict(text=thumb_text(tag, ben) or THUMB_FALLBACK[desk], kicker=loc.upper()), free_photos=[], scenes=sc,
                    sku=it['sku'], variant=it['variant'], slot_sast=it['slot'], tier=it['tier'], tier_why=it['why'])
        # no picture twice in one video: a repeat becomes a text card (product card beside it, blurred photo behind)
        usedimg = set()
        for x in item['scenes']:
            if x['type'] in ('figure', 'photo') and x.get('image'):
                if x['image'] in usedimg: x['type'] = 'note'
                usedimg.add(x['image'])
        # text cards keep a listing image of their own product (no plain backgrounds)
        for s in item['scenes']:
            if s['type'] in ('note', 'steps', 'bullets') and not s.get('image'): s['image'] = pic(k); k += 1
        narr = ' '.join(x['say'] for x in item['scenes'])
        item['script_overlap_max'] = round(max((overlap(narr, q, name) for q in prev_says.get(clean(name).lower(), [])), default=0), 2)
        if item['script_overlap_max'] > 0.6 and short:  # same product again: drop the shared description (videos keep it for length)
            item['scenes'] = [x for x in item['scenes'] if x.get('kicker') != 'WHAT IT IS']
            narr = ' '.join(x['say'] for x in item['scenes'])
            item['script_overlap_max'] = round(max((overlap(narr, q, name) for q in prev_says.get(clean(name).lower(), [])), default=0), 2)
        if item['script_overlap_max'] > 0.85:
            problems.append((it, f"script overlaps an earlier video of this product ({item['script_overlap_max']})")); continue
        ke = kit_check(f, item)
        if ke: problems.append((it, 'kit: ' + '; '.join(ke))); continue
        vids.append(item)
    spec = {'checked': date, 'note': f'{date} daily batch (skincare-daily/sk.py)', 'channels': base['channels'], 'videos': vids}
    json.dump(spec, open(f'{WORK}/{date}/features.json', 'w'), indent=1, ensure_ascii=False)
    json.dump([{'item': {k: v for k, v in a.items()}, 'problem': b} for a, b in problems], open(f'{WORK}/{date}/write_problems.json', 'w'), indent=1)
    sys.path.insert(0, LAUNCH); sys.argv = ['x']
    import feature as Fe
    bad = []
    for v in vids:
        vv = dict(v); vv['channel'] = base['channels'][v['domain']]; vv.update({x: vv['channel'][x] for x in ('locality', 'desk', 'credential_line', 'voice')})
        try: Fe.check_text(vv)
        except AssertionError as e: bad.append((v['slug'], str(e)))
    print(json.dumps({'written': len(vids), 'problems': [(a['domain'], a['slot'], b) for a, b in problems], 'text_check_fail': bad}, indent=1))


# ---------------------------------------------------------------- render + QA (+ one retry)
def render(date, only=()):
    w = f'{WORK}/{date}'; out = f'{w}/out'; os.makedirs(out, exist_ok=True); spec = json.load(open(f'{w}/features.json'))
    todo = [v['slug'] for v in spec['videos'] if (not only or v['slug'] in only) and not os.path.exists(f"{out}/{v['slug']}.json")]
    env = dict(os.environ, FEATURE_OUT=out)
    for attempt in (1, 2):
        if not todo: break
        r = subprocess.run(['python3', f'{LAUNCH}/feature.py', f'{w}/features.json', *todo], env=env, capture_output=True, text=True)
        open(f'{w}/render-{attempt}.log', 'w').write(r.stdout + r.stderr)
        todo = [s for s in todo if not os.path.exists(f'{out}/{s}.json')]
        if todo and attempt == 1:  # retry once, one at a time, so one failure doesn't block the rest
            for s in list(todo):
                r = subprocess.run(['python3', f'{LAUNCH}/feature.py', f'{w}/features.json', s], env=env, capture_output=True, text=True)
                open(f'{w}/render-retry-{s}.log', 'w').write(r.stdout + r.stderr)
            todo = [s for s in todo if not os.path.exists(f'{out}/{s}.json')]; break
    thumbs(date)  # most distinct thumbnail layout per item, before QA
    spec = json.load(open(f'{w}/features.json'))
    # QA only on what rendered
    ok = [v for v in spec['videos'] if os.path.exists(f"{out}/{v['slug']}.json")]
    json.dump(dict(spec, videos=ok), open(f'{w}/features-rendered.json', 'w'), indent=1, ensure_ascii=False)
    subprocess.run(['python3', f'{LAUNCH}/qa_feature.py', f'{w}/features-rendered.json', out], capture_output=True, text=True)
    crossday(date)
    q = json.load(open(f'{out}/qa.json'))
    print(json.dumps({'rendered': len(ok), 'not_rendered': todo, 'qa_fails': q['summary']['fails'], 'similarity_fails': len(q['summary']['similarity_fails'])}, indent=1))


def thumbs(date, only=()):
    """Per item, pick the thumbnail layout farthest (dHash) from the last 14 days and the rest of this batch."""
    sys.path.insert(0, LAUNCH); sys.argv = ['x']
    import feature as Fe, qa_feature as Q
    from PIL import Image
    w = f'{WORK}/{date}'; spec = json.load(open(f'{w}/features.json')); media = os.environ.get('SK_MEDIA', '/tmp/launch-media')
    prev = [Q.dhash(Image.open(h['thumb'])) for h in history(media) if h['thumb'] and os.path.exists(h['thumb']) and h['date'] < date
            and (dt.date.fromisoformat(date) - dt.date.fromisoformat(h['date'])).days <= 14]
    done = {}
    for v in spec['videos']:
        if only and v['slug'] not in only:
            if os.path.exists(f"{w}/out/{v['slug']}.jpg"): done[v['slug']] = Q.dhash(Image.open(f"{w}/out/{v['slug']}.jpg"))
            continue
        vv = dict(v); vv['channel'] = spec['channels'][v['domain']]; vv.update({x: vv['channel'][x] for x in ('locality', 'desk', 'credential_line', 'voice')})
        photos = list(dict.fromkeys(x['image'] for x in v['scenes'] if x.get('image') and x['image'] != v['packshot']))
        best = None
        texts = list(dict.fromkeys([v['thumb']['text'], THUMB_FALLBACK[CH[v['domain']][1]], 'How to use it']))
        for lay, txt in [(l, t) for t in texts for l in ['right', 'left', 'center', 'split'] + [('photo', p) for p in photos]]:
            if best and best[0] >= 48: break
            th = {'text': txt, 'kicker': v['thumb']['kicker']}
            th.update(layout='photo', photo=lay[1]) if isinstance(lay, tuple) else th.update(layout=lay)
            vv['thumb'] = th; Fe.thumbnail(vv, '/tmp/sk-t.jpg'); h = Q.dhash(Image.open('/tmp/sk-t.jpg'))
            d = min([Q.ham(h, o) for o in prev + list(done.values())] or [256])
            if best is None or d > best[0]: best = (d, dict(th), h)
        v['thumb'] = best[1]; vv['thumb'] = best[1]; done[v['slug']] = best[2]
        if os.path.exists(f"{w}/out/{v['slug']}.json"): Fe.thumbnail(vv, f"{w}/out/{v['slug']}.jpg")
    json.dump(spec, open(f'{w}/features.json', 'w'), indent=1, ensure_ascii=False)


def crossday(date):
    sys.path.insert(0, LAUNCH); sys.argv = ['x']
    import qa_feature as Q
    from PIL import Image
    w = f'{WORK}/{date}'; media = os.environ.get('SK_MEDIA', '/tmp/launch-media')
    prev = [Q.dhash(Image.open(h['thumb'])) for h in history(media) if h['thumb'] and os.path.exists(h['thumb']) and h['date'] < date
            and (dt.date.fromisoformat(date) - dt.date.fromisoformat(h['date'])).days <= 14]
    res = []
    for f in sorted(glob.glob(f'{w}/out/*.jpg')):
        d = min((Q.ham(Q.dhash(Image.open(f)), p) for p in prev), default=256)
        res.append({'slug': os.path.basename(f)[:-4], 'min_thumb_dist_vs_last_14_days': d, 'ok': d >= 40})
    json.dump(res, open(f'{w}/out/crossday.json', 'w'), indent=1)


# ---------------------------------------------------------------- stage + ledger for the publisher
def stage(date, media):
    w = f'{WORK}/{date}'; out = f'{w}/out'; base = f'skincare-daily/{date}'; dst = f'{media}/{base}'
    spec = json.load(open(f'{w}/features-rendered.json')); q = {r['slug']: r for r in json.load(open(f'{out}/qa.json'))['renders']}
    cross = {r['slug']: r for r in json.load(open(f'{out}/crossday.json'))}; imgs = json.load(open(f'{w}/images.json'))
    src = {x['file']: dict(file=x['file'], sku=s, source=x['url'], sha256=x['sha256'], role='packshot (variant image)' if i == 0 else 'listing image')
           for s, L in imgs.items() for i, x in enumerate(L)}
    os.makedirs(f'{dst}/images', exist_ok=True)
    old = json.load(open(f'{dst}/manifest.json')) if os.path.exists(f'{dst}/manifest.json') else {'items': []}
    items = {i['slug']: i for i in old['items']}; failed = []
    for v in spec['videos']:
        r = q[v['slug']]; c = cross.get(v['slug'], {'ok': True})
        if not (r['pass'] and c['ok']): failed.append((v['domain'], v['slot_sast'], v['slug'], 'qa' if not r['pass'] else 'too similar to an earlier thumbnail')); continue
        d = f"{dst}/renders/{v['domain']}"; os.makedirs(d, exist_ok=True); files = {}
        for ext, nm in (('.mp4', '.mp4'), ('.jpg', '.jpg'), ('.srt', '.en.srt')):
            shutil.copy2(f"{out}/{v['slug']}{ext}", f"{d}/{v['slug']}{nm}"); files[nm] = f"{base}/renders/{v['domain']}/{v['slug']}{nm}"
        assert sha(f"{d}/{v['slug']}.mp4") == r['mp4_sha256']
        ims = sorted({v['packshot']} | {s['image'] for s in v['scenes'] if s.get('image')})
        for i in ims: shutil.copy2(f'{STORE}/{i}', f'{dst}/images/{i}')
        meta = json.load(open(f"{out}/{v['slug']}.json"))
        items[v['slug']] = {'domain': v['domain'], 'handle': CH[v['domain']][0], 'slot_sast': f"{date} {v['slot_sast']}", 'format': v['format'],
            'slug': v['slug'], 'sku': v['sku'], 'variant': v['variant'], 'selection': {'tier': v['tier'], 'why': v['tier_why']},
            'product': {'name': v['product_name'], 'listing_url': v['product_url'], 'checked': date, 'packshot': f"{base}/images/{v['packshot']}",
                        'packshot_sha256': src[v['packshot']]['sha256'], 'packshot_source': src[v['packshot']]['source']},
            'title': meta['title'], 'description': meta['description'], 'tags': meta['tags'], 'category': 'Howto & Style',
            'default_language': 'en', 'audio_language': 'en', 'made_for_kids': False, 'paid_promotion': True, 'altered_or_synthetic_content': False,
            'duration_seconds': r['duration'], 'resolution': f"{r['w']}x{r['h']}",
            'media_path': files['.mp4'], 'media_url': RAW + files['.mp4'], 'sha256': r['mp4_sha256'],
            'thumbnail_path': files['.jpg'], 'thumbnail_url': RAW + files['.jpg'], 'thumbnail_sha256': r['jpg_sha256'],
            'captions_path': files['.en.srt'], 'captions_url': RAW + files['.en.srt'], 'captions_sha256': sha(f"{d}/{v['slug']}.en.srt"),
            'listing_images': [f'{base}/images/{i}' for i in ims], 'narration': f"Kokoro text-to-speech, voice {spec['channels'][v['domain']]['voice']} (American English, female)",
            'music': 'original, made for this video', 'qa': {k: r[k] for k in ('lufs', 'true_peak', 'packshot_match', 'srt_cues', 'pass')},
            'crossday_min_thumb_dist': c.get('min_thumb_dist_vs_last_14_days'), 'status': 'ready'}
    S = json.load(open(f'{dst}/images/sources.json')) if os.path.exists(f'{dst}/images/sources.json') else []
    have = {s['file'] for s in S}
    for it in items.values():
        for p in it['listing_images']:
            f = p.rsplit('/', 1)[1]
            if f not in have and f in src: S.append(src[f]); have.add(f)
    json.dump(sorted(S, key=lambda x: x['file']), open(f'{dst}/images/sources.json', 'w'), indent=1)
    allit = sorted(items.values(), key=lambda x: (x['domain'], x['slot_sast'])); chan = {}
    for it in allit:
        c = chan.setdefault(it['handle'], {'domain': it['domain'], 'shorts': 0, 'videos': 0, 'all_pass': True})
        c['shorts' if it['format'] == 'short' else 'videos'] += 1; c['all_pass'] &= it['qa']['pass']
    for c in chan.values():
        c['status'] = 'ready' if c['all_pass'] and c['shorts'] == 4 and c['videos'] == 2 else 'partial: staged items ready'
    pl = json.load(open(f'{w}/plan.json')); heal_run = any(i.get('existing') for i in pl['items'])
    sfx = f"-heal-{dt.date.today().isoformat()}" if heal_run else ''  # a heal run never overwrites the day's original plan/features/QA
    shutil.copy2(f'{out}/qa.json', f'{dst}/qa{sfx}.json'); shutil.copy2(f'{out}/crossday.json', f'{dst}/crossday{sfx}.json')
    shutil.copy2(f'{w}/plan.json', f'{dst}/plan{sfx}.json'); shutil.copy2(f'{w}/features.json', f'{dst}/features{sfx}.json')
    probs = json.load(open(f'{w}/write_problems.json')) if os.path.exists(f'{w}/write_problems.json') else []
    have_slots = {(it['handle'], it['slot_sast'][11:16]) for it in allit}; old_un = {(u['handle'], u['slot_sast'][11:16]): u for u in old.get('unfilled_slots', [])}
    unfilled = []
    for dom, (h, _) in CH.items():
        for s_ in SHORT_SLOTS + VIDEO_SLOTS:
            if (h, s_) in have_slots: continue
            why = next((b['problem'] for b in probs if b['item']['domain'] == dom and b['item']['slot'] == s_), None) \
                or next((f'not staged: {x[3]}' for x in failed if x[0] == dom and x[1] == s_), None) \
                or (old_un.get((h, s_)) or {}).get('reason') or 'not produced in this run'
            unfilled.append({'handle': h, 'slot_sast': f'{date} {s_}', 'format': 'short' if s_ in SHORT_SLOTS else 'regular', 'reason': why})
    json.dump({'date': date, 'ledger': f'{base}/receipt-ledger.json', 'publishing': 'skincare-upload.yml (GitHub Action) publishes; this batch uploads and schedules nothing.',
               'commission_disclosure': 'description only', 'language': 'American English', 'channels': chan, 'not_staged': failed,
               'unfilled_slots': unfilled, 'items': allit},
              open(f'{dst}/manifest.json', 'w'), indent=1, ensure_ascii=False)
    verify(media, date); ledger(media, date)
    print(json.dumps({'staged': len(allit), 'not_staged': failed, 'unfilled': [(u['handle'], u['slot_sast']) for u in unfilled], 'channels': {k: v['status'] for k, v in chan.items()}}, indent=1))
    return failed


def verify(media, date):
    m = json.load(open(f'{media}/skincare-daily/{date}/manifest.json')); bad = []
    for it in m['items']:
        for p, k in (('media_path', 'sha256'), ('thumbnail_path', 'thumbnail_sha256'), ('captions_path', 'captions_sha256')):
            if sha(f'{media}/{it[p]}') != it[k]: bad.append(it[p])
    if bad: raise SystemExit(f'hash mismatch: {bad}')
    return len(m['items'])


def ledger(media, date):
    """Write/refresh the rows the publisher reads. Never touches a row that already has a youtube_id; never invents one."""
    f = f'{media}/skincare-daily/{date}/receipt-ledger.json'; m = json.load(open(f'{media}/skincare-daily/{date}/manifest.json'))
    L = json.load(open(f)) if os.path.exists(f) else {'date': date, 'timezone': 'Africa/Johannesburg', 'items': []}
    rows = {(r['channel'], r['time']): r for r in L['items']}
    for it in m['items']:
        key = (it['handle'], it['slot_sast'][11:16]); r = rows.get(key, {'channel': it['handle'], 'time': key[1]})
        if r.get('youtube_id'): continue
        if r.get('manifest_slug') not in (None, it['slug']) and r.get('status') not in ('missing_render', None): continue
        r.update({'format': 'short' if it['format'] == 'short' else 'regular', 'status': 'staged_awaiting_youtube_receipt', 'youtube_id': None,
                  'sku': it['sku'], 'title': it['title'], 'manifest_slug': it['slug'], 'media_sha256': it['sha256'], 'asset_checksums_verified': True})
        r.pop('reason', None); rows[key] = r
    L['items'] = sorted(rows.values(), key=lambda r: (r['channel'], r['time']))
    rec = L.setdefault('reconciliation', {})
    rec['staged_files_verified'] = sum(1 for r in L['items'] if r.get('asset_checksums_verified'))
    rec['missing_renders'] = sum(1 for r in L['items'] if r.get('status') == 'missing_render')
    rec['youtube_ids_recorded'] = sum(1 for r in L['items'] if r.get('youtube_id'))
    rec['producer_refreshed'] = dt.datetime.now(dt.timezone(dt.timedelta(hours=2))).isoformat(timespec='minutes')
    json.dump(L, open(f, 'w'), indent=2, ensure_ascii=False)


def heal(media, today):
    """Earlier days: report items still missing a render or not in the ledger; refresh ledger rows from manifests."""
    out = []
    for d in sorted(glob.glob(f'{media}/skincare-daily/2026-*')):
        date = os.path.basename(d)
        if date >= today or not os.path.exists(f'{d}/manifest.json'): continue
        ledger(media, date)
        L = json.load(open(f'{d}/receipt-ledger.json'))
        miss = [(r['channel'], r['time']) for r in L['items'] if r.get('status') == 'missing_render']
        have = {(r['channel'], r['time']) for r in L['items']}
        gaps = [(h, s) for dom, (h, _) in CH.items() for s in SHORT_SLOTS + VIDEO_SLOTS if (h, s) not in have]
        out.append({'date': date, 'missing_render': miss, 'no_row': gaps, 'awaiting_youtube_id': sum(1 for r in L['items'] if r.get('status') == 'staged_awaiting_youtube_receipt')})
    print(json.dumps(out, indent=1)); return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'plan': plan(a[1], a[2], a[3])
    elif a[0] == 'planheal': planheal(a[1], a[2], a[3])
    elif a[0] == 'fetchjs': print('\n\n'.join(fetchjs(a[1], a[2])))
    elif a[0] == 'ingest': ingest(a[1], a[2:])
    elif a[0] == 'write':  # write, then replan any slot write could not fill (at most 3 rounds)
        write(a[1])
        for _ in range(3):
            if not replan(a[1], os.environ.get('SK_MEDIA', '/tmp/launch-media')): break
            write(a[1])
    elif a[0] == 'render': render(a[1], a[2:])
    elif a[0] == 'thumbs': thumbs(a[1], a[2:])
    elif a[0] == 'stage': stage(a[1], a[2])
    elif a[0] == 'heal': heal(a[1], a[2] if len(a) > 2 else '9999')
    elif a[0] == 'ledger': ledger(a[1], a[2])
