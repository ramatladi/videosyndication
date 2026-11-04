#!/usr/bin/env python3
"""Beautiful Ladies Only: build a day's Shorts/videos from Unsplash photos + Mirage Tropical Records tracks.

Usage: python3 build.py days_YYYY-MM-DD.json [name ...]
Day file: list of {"name","W","H","secs","track_url","start","photos":[[unsplash_slug, caption], ...]}
Every slug must be in ledger.json "photos" (image id + photographer) before building.
Outputs go to ./out/<name>.mp4 (git-ignored). Needs ffmpeg + Pillow + Poppins fonts.
"""
import json, os, subprocess, sys, urllib.request
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
OUT = os.path.join(HERE, "out")
FONT_DIRS = ["/usr/share/fonts/truetype/google-fonts", os.path.join(WORK, "fonts")]
for d in (WORK, OUT, os.path.join(WORK, "img"), os.path.join(WORK, "music"), os.path.join(WORK, "fonts")):
    os.makedirs(d, exist_ok=True)
LEDGER = json.load(open(os.path.join(HERE, "ledger.json")))["photos"]


def font(name):
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    p = os.path.join(WORK, "fonts", name)
    urllib.request.urlretrieve(f"https://github.com/google/fonts/raw/main/ofl/poppins/{name}", p)
    return p


FONT_B, FONT_L = font("Poppins-Bold.ttf"), font("Poppins-LightItalic.ttf")


def fetch(url, path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        subprocess.run(["curl", "-sSfL", "-m", "120", "-o", path, url], check=True)
    return path


def photo(slug):
    return fetch(f"https://images.unsplash.com/{LEDGER[slug]['image']}?w=1440&q=85&fm=jpg",
                 os.path.join(WORK, "img", slug + ".jpg"))


def seg(name, slug, caption, W, H, secs, idx):
    fps, frames = 30, int(secs * 30)
    src = photo(slug)
    iw, ih = Image.open(src).size
    s = min(W / iw, H / ih)
    fw, fh = int(iw * s) // 2 * 2, int(ih * s) // 2 * 2
    cap_f, cr_f = f"{WORK}/{name}_c{idx}.txt", f"{WORK}/{name}_r{idx}.txt"
    open(cap_f, "w").write(caption)
    open(cr_f, "w").write(f"Photo: {LEDGER[slug]['photographer']} / Unsplash")
    vert = H > W
    big, small = (64, 30) if vert else (54, 26)
    ytop = int(H * (0.11 if vert else 0.07))
    z = "min(zoom+0.0007,1.10)" if idx % 2 == 0 else "if(eq(on,0),1.10,max(zoom-0.0007,1.0))"
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:2,eq=brightness=-0.12,fps={fps}[bg];"
        f"[1:v]scale={fw*2}:{fh*2},zoompan=z='{z}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={fw}x{fh}:fps={fps}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,"
        f"drawtext=fontfile={FONT_B}:textfile={cap_f}:fontsize={big}:fontcolor=white:borderw=3:bordercolor=black@0.6:"
        f"x=(w-text_w)/2:y={ytop}:alpha='if(lt(t,0.6),t/0.6,if(gt(t,{secs-0.6}),({secs}-t)/0.6,1))',"
        f"drawtext=fontfile={FONT_L}:textfile={cr_f}:fontsize={small}:fontcolor=white@0.9:borderw=2:bordercolor=black@0.6:"
        f"x=(w-text_w)/2:y=h-{int(H*0.08)},"
        f"drawtext=fontfile={FONT_B}:text='Beautiful Ladies Only':fontsize={small}:fontcolor=white@0.85:borderw=2:bordercolor=black@0.5:"
        f"x=(w-text_w)/2:y=h-{int(H*0.08)}-{small+16},"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={secs-0.4}:d=0.4,format=yuv420p[v]"
    )
    out = f"{WORK}/{name}_s{idx}.mp4"
    # input 0 loops for the blurred background; input 1 is a single frame for zoompan (looping it OOMs)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", str(secs), "-i", src, "-i", src,
                    "-filter_complex", fc, "-map", "[v]", "-t", str(secs), "-r", str(fps),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out], check=True)
    return out


def build(sp):
    name, W, H, secs = sp["name"], sp["W"], sp["H"], sp["secs"]
    track = fetch(sp["track_url"], os.path.join(WORK, "music", os.path.basename(sp["track_url"])))
    segs = [seg(name, p, c, W, H, secs, i) for i, (p, c) in enumerate(sp["photos"])]
    lst = f"{WORK}/{name}_list.txt"
    open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
    total = secs * len(segs)
    out = f"{OUT}/{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-ss", str(sp.get("start", 0)), "-i", track,
                    "-filter_complex", f"[1:a]afade=t=in:st=0:d=1.5,afade=t=out:st={total-3}:d=3[a]",
                    "-map", "0:v", "-map", "[a]", "-t", str(total), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True)
    for s in segs:
        os.remove(s)
    print(name, total, "s ->", out, flush=True)


if __name__ == "__main__":
    specs = json.load(open(sys.argv[1]))
    only = sys.argv[2:]
    for sp in specs:
        if not only or sp["name"] in only:
            build(sp)
