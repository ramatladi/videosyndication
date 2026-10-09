import sys, json, os
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
EP = json.load(open(sys.argv[1]))
WORK = os.environ.get("WORK", "/tmp/wisewords_work"); os.makedirs(os.path.join(WORK, "wav"), exist_ok=True)
M = os.path.expanduser("~/.cache/kokoro")
voice, speed = EP.get("voice", "am_onyx"), float(EP.get("speed", 0.84))
k = Kokoro(os.path.join(M, "kokoro.onnx"), os.path.join(M, "voices.bin"))
out = []
for si, seg in enumerate(EP["segments"]):
    for li, line in enumerate(seg["lines"]):
        a, sr = k.create(line, voice=voice, speed=speed, lang="en-us")
        idx = np.where(np.abs(a) > 0.01)[0]
        a = a[max(idx[0] - 600, 0): idx[-1] + 1200]
        p = os.path.join(WORK, "wav", f"{si}_{li}.wav")
        sf.write(p, a, sr)
        out.append({"seg": si, "line": li, "path": p, "dur": len(a) / sr, "sr": sr})
json.dump(out, open(os.path.join(WORK, "lines.json"), "w"), indent=1)
print("total speech", round(sum(o["dur"] for o in out), 2), "s in", len(out), "lines")
