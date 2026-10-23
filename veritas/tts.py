"""Voice for a Veritas Recruitment Agency job video: one natural Kokoro voice reads every line.

usage: python3 veritas/tts.py veritas/jobs/vraNNN.json
Writes $WORK/wav/<scene>_<line>.wav and $WORK/lines.json (scene, line, path, duration).
"""
import sys, json, os
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

JOB = json.load(open(sys.argv[1]))
WORK = os.environ.get("WORK", "/tmp/veritas_work"); os.makedirs(os.path.join(WORK, "wav"), exist_ok=True)
M = os.path.expanduser("~/.cache/kokoro")
voice, speed = JOB.get("voice", "af_heart"), float(JOB.get("speed", 1.0))
k = Kokoro(os.path.join(M, "kokoro.onnx"), os.path.join(M, "voices.bin"))
out = []
for si, scene in enumerate(JOB["scenes"]):
    for li, line in enumerate(scene["lines"]):
        a, sr = k.create(line, voice=voice, speed=speed, lang="en-us")
        idx = np.where(np.abs(a) > 0.01)[0]
        a = a[max(idx[0] - 600, 0): idx[-1] + 1500]
        p = os.path.join(WORK, "wav", f"{si}_{li}.wav")
        sf.write(p, a, sr)
        out.append({"scene": si, "line": li, "path": p, "dur": len(a) / sr, "sr": sr})
json.dump(out, open(os.path.join(WORK, "lines.json"), "w"), indent=1)
print("speech", round(sum(o["dur"] for o in out), 1), "s in", len(out), "lines")
