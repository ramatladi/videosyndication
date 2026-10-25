"""Machine "ears": what a trained music tagger hears in a track.

Uses musicnn's MSD model (Pons & Serra; trained on the Million Song Dataset's 50 most common listener tags; weights
ship inside the pip package) to estimate how much a render sounds like House / electronic / dance / chillout versus
rock, blues, jazz, punk... It is a listener model, not a quality guarantee — but it hears the audio, which the
technical QC does not.

    TF_USE_LEGACY_KERAS=1 python3 djvelvetgrey/v2/ears.py track.mp3 [more.mp3 ...]      -> JSON per file
Requires: pip install tensorflow-cpu tf_keras librosa; pip install --no-deps musicnn
"""
import json, os, sys
os.environ.setdefault('TF_USE_LEGACY_KERAS', '1'); os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
import numpy as np

GOOD = ['House', 'electronic', 'dance', 'electronica', 'chillout', 'chill', 'electro', 'instrumental', 'party', 'catchy',
        'sexy', 'ambient', 'Mellow', 'beautiful']
BAD = ['rock', 'alternative', 'indie', 'punk', 'metal', 'hard rock', 'classic rock', 'blues', 'country', 'folk', 'oldies',
       'jazz', 'heavy metal', 'Progressive rock', 'alternative rock', 'indie rock', '60s', '70s']


def ensure_deps(timeout=900):
    """Install the listener model's dependencies if missing (scheduled runs start from a fresh machine)."""
    import importlib.util, subprocess
    need = [m for m, pkg in (('tensorflow', 'tensorflow-cpu'), ('tf_keras', 'tf_keras'), ('librosa', 'librosa')) if importlib.util.find_spec(m) is None]
    pk = {'tensorflow': 'tensorflow-cpu', 'tf_keras': 'tf_keras', 'librosa': 'librosa'}
    if need: subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--break-system-packages'] + [pk[m] for m in need], timeout=timeout, check=True)
    if importlib.util.find_spec('musicnn') is None:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--break-system-packages', '--no-deps', 'musicnn'], timeout=timeout, check=True)


def _patch():
    import librosa
    from musicnn import extractor as X, configuration as config

    def batch_data(audio_file, n_frames, overlap):          # same as musicnn's, without its float16 overflow on loud masters
        audio, sr = librosa.load(audio_file, sr=config.SR)
        rep = librosa.feature.melspectrogram(y=audio, sr=sr, hop_length=config.FFT_HOP, n_fft=config.FFT_SIZE,
                                             n_mels=config.N_MELS).T.astype(np.float32)
        rep = np.log10(10000 * rep + 1)
        last = rep.shape[0] - n_frames + 1; out = []
        for t in range(0, max(1, last), overlap):
            p = rep[t:t + n_frames]
            if len(p) == n_frames: out.append(p)
        return np.stack(out), rep
    X.batch_data = batch_data
    return X


def listen(path):
    import tensorflow as tf
    tf.compat.v1.disable_eager_execution()
    X = _patch()
    taggram, tags = X.extractor(path, model='MSD_musicnn', extract_features=False)
    m = taggram.mean(0); d = {t: float(v) for t, v in zip(tags, m)}
    good = sum(d.get(t, 0) for t in GOOD); bad = sum(d.get(t, 0) for t in BAD)
    return {'file': os.path.basename(path), 'top': [(t, round(d[t], 3)) for t in sorted(d, key=lambda k: -d[k])[:10]],
            'house': round(d.get('House', 0), 3), 'electronic': round(d.get('electronic', 0), 3), 'dance': round(d.get('dance', 0), 3),
            'genre_fit': round(good / (good + bad + 1e-9), 3)}


if __name__ == '__main__':
    import subprocess
    if len(sys.argv) > 2:      # one process per file (the TF1 graph is built per call)
        for f in sys.argv[1:]: subprocess.run([sys.executable, __file__, f])
    else:
        print(json.dumps(listen(sys.argv[1])))
