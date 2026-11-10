#!/usr/bin/env python3
"""Beautiful Ladies Only: Mirage Tropical Records music pool and rotation.

    python3 tracks.py sync              # add newly released Mirage tracks to tracks.json
    python3 tracks.py pick YYYY-MM-DD   # print the day's track per slot (least recently used first)
    python3 tracks.py list              # pool with use counts and last use

Source of new tracks: mirage/ledger.json releases whose "generated" block has a completed Creative Claw
audio_url (cdn.creativeclaw.co). Those are released Mirage Tropical Records tracks. Never generate music here.
"""
import glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
POOL = os.path.join(HERE, "tracks.json")
MIRAGE = os.path.join(HERE, "..", "mirage", "ledger.json")
SLOTS = ["short1", "short2", "short3", "short4", "video1", "video2"]
STYLE = {"deep": "Deep house", "futurebass": "Future bass", "melodic": "Melodic organic house", "tech": "Tech house",
         "house": "House", "vocal": "Vocal house", "afro": "Afro house", "disco": "Disco", "nudisco": "Nu-disco",
         "tropical": "Tropical house", "soulful": "Soulful house", "progressive": "Progressive house",
         "trance": "Trance", "indiedance": "Indie dance", "french": "French house"}
MIN_SECS = 180 + 5  # a video needs 3:00 from 0; a Short needs start (40-60) + 30


def load():
    return json.load(open(POOL))


def save(pool):
    json.dump(pool, open(POOL, "w"), indent=1)
    open(POOL, "a").write("\n")


def duration(url):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", url],
                       capture_output=True, text=True, timeout=120)
    return float(r.stdout.strip() or 0)


def sync():
    pool = load()
    have = {t["audio_url"] for t in pool["tracks"]}
    added = []
    for r in json.load(open(MIRAGE))["releases"]:
        g = r.get("generated") or {}
        url = g.get("audio_url") if isinstance(g, dict) else None
        if not url or "cdn.creativeclaw.co" not in url or url in have:
            continue
        secs = duration(url)
        if secs < MIN_SECS:
            print(f"skip {r['release']}: {secs:.0f}s is too short")
            continue
        t = {"id": r["release"], "title": r["title"], "artist": r.get("artist"),
             "style": STYLE.get(r.get("style"), (r.get("style") or "house").title()),
             "audio_url": url, "secs": round(secs), "added": r.get("date")}
        pool["tracks"].append(t)
        have.add(url)
        added.append(t)
    save(pool)
    for t in added:
        print(f"added {t['id']} \"{t['title']}\" by {t['artist']} ({t['style']}, {t['secs']}s)")
    print(f"{len(added)} new, {len(pool['tracks'])} in pool")


def usage():
    """{audio_url: (last_date, count)} from every days_*.json."""
    use = {}
    for f in sorted(glob.glob(os.path.join(HERE, "days_*.json"))):
        day = os.path.basename(f)[5:15]
        for sp in json.load(open(f)):
            last, n = use.get(sp["track_url"], ("", 0))
            use[sp["track_url"]] = (max(last, day), n + 1)
    return use


def pick(day):
    pool, use = load(), usage()
    order = sorted(pool["tracks"], key=lambda t: (use.get(t["audio_url"], ("", 0)), t["added"] or ""))
    # spread the pool over the 6 slots; repeat only when the pool has fewer than 6 tracks
    starts = [40, 45, 50, 55, 60]
    k = int(day.replace("-", "")) % len(starts)
    out = []
    for i, name in enumerate(SLOTS):
        t = order[i % len(order)]
        start = 0 if name.startswith("video") else starts[(k + i) % len(starts)]
        out.append({"name": name, "track_url": t["audio_url"], "start": start, "style": t["style"],
                    "title": t["title"], "artist": t["artist"]})
    print(json.dumps(out, indent=1))


def listing():
    use = usage()
    for t in load()["tracks"]:
        last, n = use.get(t["audio_url"], ("never", 0))
        print(f"{t['id']:8} {t['style']:24} {t['title']!s:30} uses={n:<3} last={last}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "sync":
        sync()
    elif cmd == "pick":
        pick(sys.argv[2])
    else:
        listing()
