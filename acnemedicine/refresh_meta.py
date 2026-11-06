"""Recreate scene timings for videos built before timings were recorded, by re-synthesising only the narration
(Kokoro is deterministic, so the lengths match the published audio), and check them against the real video length.

    python3 acnemedicine/refresh_meta.py acne <plan.json> <id> ...      -> out/<date>/<id>.timing.json
    python3 acnemedicine/refresh_meta.py launch <slug> ...               -> skincare-launch/out/<slug>.timing.json
"""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)


def lengths(says, voice, pad):
    from kokoro_onnx import Kokoro
    m = os.path.expanduser('~/.cache/kokoro'); k = Kokoro(f'{m}/kokoro.onnx', f'{m}/voices.bin')
    out = []
    for s in says:
        a, sr = k.create(s, voice=voice, speed=1.0, lang='en-us' if voice[0] == 'a' else 'en-gb')
        out.append(round((len(a) + 2 * int(sr * pad)) / sr, 3))
    return out


def duration(mp4):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4]))


def save(says, voice, pad, mp4, dest):
    d = lengths(says, voice, pad)
    real = duration(mp4) if os.path.exists(mp4) else None
    if real is not None and abs(sum(d) - real) > 0.6:
        sys.exit(f'{dest}: narration {sum(d):.2f}s vs video {real:.2f}s; timings would drift, not writing')
    json.dump({'scenes': d, 'pad': pad, 'rebuilt': True}, open(dest, 'w'))
    print(dest, f'{sum(d):.1f}s', f'(video {real:.1f}s)' if real else '')


if __name__ == '__main__':
    kind, *rest = sys.argv[1:]
    if kind == 'acne':
        plan = json.load(open(rest[0])); out = f"{ROOT}/out/{plan['date']}"
        for it in plan['items']:
            if it['id'] in rest[1:]:
                save([s['say'] for s in it['scenes']], 'af_heart', 0.35, f"{out}/{it['id']}.mp4", f"{out}/{it['id']}.timing.json")
    else:
        spec = json.load(open(f'{ROOT}/skincare-launch/specs.json'))
        for v in spec['videos']:
            if v['slug'] in rest:
                o = f"{ROOT}/skincare-launch/out/{v['slug']}"
                save([s['say'] for s in v['scenes']], v['voice'], 0.4, o + '.mp4', o + '.timing.json')
