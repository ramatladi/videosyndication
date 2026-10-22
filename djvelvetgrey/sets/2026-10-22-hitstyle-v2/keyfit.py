import json, sys, numpy as np, librosa
sys.path.insert(0, '/home/claude/videosyndication/djvelvetgrey/v2')
import styles as S
MODES = {'major': [0,2,4,5,7,9,11], 'minor': [0,2,3,5,7,8,10], 'dorian': [0,2,3,5,7,9,10], 'mixolydian': [0,2,4,5,7,9,10]}
HOOKS = {  # song style: (file, region)
 'disco': ('365849_many-lovers.mp3', [0.7, 22.6]), 'nudisco': ('251829_female-voice.mp3', [5.3, 13.7]),
 'afro': ('427418_get-down.mp3', [0.5, 11.3]), 'deep': ('537090_love-vocal.mp3', [0.05, 3.25]),
 'melodic': ('523227_morning-country-female-vocal-loop.mp3', [0, 18.65]), 'tropical': ('508456_female-voice-doodling.mp3', [1.1, 6.4]),
 'house': ('469018_vocal3.mp3', [0, 3.69]), 'vocal': ('448705_hey-hey-hey-yeah.mp3', [0.6, 5.35]),
 'tech': ('362340_short-vocals-100bpm.mp3', [1.8, 7.85]), 'progressive': ('529476_hip-vocal-dance-loop-100bpm.mp3', [0, 7.3])}
res = {}
for st, (f, (a, b)) in HOOKS.items():
    y, sr = librosa.load('/tmp/vox/src/' + f, sr=22050, offset=a, duration=b - a)
    f0, v, _ = librosa.pyin(y, fmin=70, fmax=1100, sr=sr, frame_length=1024)
    fr = f0[v & ~np.isnan(f0)]; midi = librosa.hz_to_midi(fr); c = float(np.median(midi - np.round(midi)))
    h = np.bincount(np.round(midi - c).astype(int) % 12, minlength=12).astype(float); h /= h.sum()
    best = []
    for mode in S.STYLES[st]['modes']:
        for tonic in range(55, 63):
            for k in (-2, -1, 0, 1, 2):          # semitone shift applied to the voice
                fit = sum(h[p] for p in range(12) if (p + k - tonic) % 12 in MODES[mode])
                best.append((round(fit - .03 * abs(k), 3), round(fit, 3), tonic, mode, k))
    best.sort(reverse=True)
    res[st] = {'file': f, 'cents': round(c * 100), 'voiced_frames': int(len(fr)), 'top': best[:6]}
    print(st, f, 'cents', round(c*100), 'frames', len(fr), best[:4])
json.dump(res, open('/tmp/vox2/keyfit.json', 'w'), indent=1)
