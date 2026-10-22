"""Technical check of a vocal version: python3 -I check_vocals.py NN [NN ...]
Loudness/peak of the mix; per drop: vocal onset distance from the 16th grid and share of voiced frames in the song's scale."""
import sys, json, numpy as np, librosa, soundfile as sf, pyloudnorm as pyln
MODES = {'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10], 'dorian': [0, 2, 3, 5, 7, 9, 10], 'mixolydian': [0, 2, 4, 5, 7, 9, 10]}
D = '/home/claude/dvg-take2'
for nn in sys.argv[1:]:
    m = json.load(open(f'{D}/{nn}v.json')); b = m['brief']; bpm = b['bpm']; bar = 240 / bpm; six = bar / 16
    scale = {(b['tonic'] + i) % 12 for i in MODES[b['mode']]}
    x, sr = sf.read(f'{D}/{nn}v.wav'); lufs = pyln.Meter(sr).integrated_loudness(x); pk = 20 * np.log10(np.abs(x).max())
    v, _ = librosa.load(f'{D}/{nn}v_vocals_only.wav', sr=22050, mono=True)
    rows = []
    for s in m['sections']:
        if not s['name'].startswith('drop'): continue
        seg = v[int(s['start_s'] * 22050):int((s['start_s'] + s['bars'] * bar) * 22050)]
        on = librosa.onset.onset_detect(y=seg, sr=22050, units='time', hop_length=128)
        dev = np.median(np.abs(((on + six / 2) % six) - six / 2)) * 1000 if len(on) else float('nan')
        f0, vf, _ = librosa.pyin(seg, fmin=70, fmax=1100, sr=22050, frame_length=1024)
        f = f0[vf & ~np.isnan(f0)]
        fit = np.mean([p in scale for p in np.round(librosa.hz_to_midi(f)).astype(int) % 12]) if len(f) > 20 else float('nan')
        rows.append(f"{s['name']} grid {dev:4.1f} ms in-key {fit:.2f}")
    print(f"{nn} {m['title'][:20]:20} {m['key']:10} LUFS {lufs:6.2f} peak {pk:5.2f} | " + ' | '.join(rows))
