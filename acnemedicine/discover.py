"""Search/discovery metadata for the skincare channels: tags, hashtags, chapters and caption files.

Used by day.py (daily Acne Medicine posts) and refresh_meta.py (already-built or already-uploaded videos).
Every helper works from the narration text and the scene timings the builders record, so nothing is invented.
"""
import json, os, re

BASE_TAGS = ['dermalogica', 'dermalogica south africa', 'skincare south africa', 'johannesburg skincare',
             'skincare routine', 'acne medicine johannesburg']
TAG_LIMIT = 400          # YouTube counts the comma-joined length; the uploader also enforces 400


def camel(s):
    return ''.join(w[:1].upper() + w[1:] for w in re.split(r'[^A-Za-z0-9]+', s) if w)


def tags(product, extra=(), base=BASE_TAGS):
    """Specific phrases first (what people type), then the channel's standing tags, deduplicated, within the limit."""
    want = [f'dermalogica {product}', product, f'how to use {product}', f'{product} review', *extra, *base]
    out = []
    for t in want:
        t = re.sub(r'\s+', ' ', t.strip().lower())
        if t and t not in out and len(', '.join(out + [t])) <= TAG_LIMIT - 20:   # room for the uploader's marker tag
            out.append(t)
    return out


def hashtags(product, region='SkincareSouthAfrica'):
    """YouTube shows the first three description hashtags above the title."""
    return f'#Dermalogica #{camel(product)} #{region}'


def timing_from_audio(scene_seconds, pad=0.35):
    """[(start, end, speech_start, speech_end)] from per-scene audio lengths (each scene has `pad` silence at both ends)."""
    t, out = 0.0, []
    for d in scene_seconds:
        out.append((t, t + d, t + pad, t + d - pad)); t += d
    return out


def chapters(captions, timing, min_len=10.0):
    """YouTube chapters: start 0:00, at least 3, each at least 10 s. Scenes shorter than that are grouped with the
    next ones; a group is named after its longest scene (the opening group keeps the opening scene's name)."""
    groups, cur = [], None
    for cap, (s, e, *_) in zip(captions, timing):
        if cur is None:
            cur = {'start': s, 'end': e, 'scenes': [(e - s, cap)]}
        else:
            cur['end'] = e; cur['scenes'].append((e - s, cap))
        if cur['end'] - cur['start'] >= min_len:
            groups.append(cur); cur = None
    if cur is not None:
        if groups:
            groups[-1]['end'] = cur['end']; groups[-1]['scenes'] += cur['scenes']
        else:
            groups.append(cur)
    if len(groups) < 3:
        return ''
    rows = []
    for i, g in enumerate(groups):
        lab = g['scenes'][0][1] if i == 0 else max(g['scenes'], key=lambda x: x[0])[1]
        rows.append((0.0 if i == 0 else g['start'], short_label(lab)))
    return '\n'.join(f'{int(s // 60)}:{int(s % 60):02d} {lab}' for s, lab in rows)


def short_label(cap, n=48):
    cap = re.split(r'\.\s|—', cap)[0].strip() or cap
    return cap if len(cap) <= n else cap[:n].rsplit(' ', 1)[0] + '…'


def srt(says, timing):
    """Caption file from the exact narration: each scene's speech is split by sentence, timed by length."""
    cues, k = [], 1
    for say, (_, _, s0, s1) in zip(says, timing):
        parts = [p for p in re.split(r'(?<=[.!?])\s+', say.strip()) if p]
        total = sum(len(p) for p in parts) or 1
        t = s0
        for p in parts:
            d = (s1 - s0) * len(p) / total
            for chunk in _lines(p):
                cd = d * len(chunk) / len(p)
                cues.append(f'{k}\n{_ts(t)} --> {_ts(t + cd)}\n{chunk}\n'); k += 1; t += cd
    return '\n'.join(cues)


def _lines(text, width=84):
    words, out, cur = text.split(), [], ''
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            out.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip()
    return out + [cur]


def _ts(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def read_timing(path):
    """Builders write <video>.timing.json: {"scenes": [seconds, ...]}."""
    if os.path.exists(path):
        return timing_from_audio(json.load(open(path))['scenes'])
    return None
