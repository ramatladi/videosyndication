import json
H = json.load(open('/tmp/vox2/hits2.json'))
PH = [("Sean Oulashin", "https://unsplash.com/photos/seashore-during-golden-hour-KMn4VEeEPR8"),
      ("llxvisuals", "https://unsplash.com/photos/palm-trees-silhouetted-against-a-vibrant-sunset-sky-VmRQHXHfygw"),
      ("Onofre Quezada", "https://unsplash.com/photos/tropical-river-winding-through-lush-jungle-with-mountains-in-background-MA9sLbbIE3g"),
      ("Wendi Wells", "https://unsplash.com/photos/a-wooden-pier-with-a-thatched-roof-over-the-ocean-OSw0NOptNu8"),
      ("Armand Mckenzie", "https://unsplash.com/photos/turquoise-water-and-white-sandbars-with-green-hills-a_-xp8Ju_b4"),
      ("Ittemaldiviano", "https://unsplash.com/photos/green-palm-tree-on-white-sand-beach-during-daytime-jmkMl20jNS0"),
      ("Vivek Panwar", "https://unsplash.com/photos/longtail-boats-on-koh-phi-phi-_ZavQnIScwM"),
      ("Yegor Denisov", "https://unsplash.com/photos/seashore-during-golden-hour-yIpU0HMpN0I"),
      ("Geio Tischler", "https://unsplash.com/photos/an-aerial-view-of-an-island-in-the-middle-of-the-ocean-_D_zFmpg8nE"),
      ("Jared Rice", "https://unsplash.com/photos/white-sand-beach-in-el-nido-Tm0XygW6gN8")]
MOOD = ["a sunset disco groove with a brass section, vibraphone, strings and a funky fretless bass for golden-hour drives along the coast",
        "a neon-lit nu-disco cruise with electric piano chords and a funky bass for late-night city lights",
        "a hypnotic afro house journey with xylophone, celesta and deep drums under a jungle sky",
        "a warm deep house night swim: soft electric piano, music box sparkles and a walking bass",
        "a melodic house drift over turquoise sandbars, with kalimba, pan flute and wide strings",
        "a bright tropical house morning with marimba and harp on a white-sand beach",
        "a sunny piano house groove with organ stabs for rooftop afternoons",
        "an uplifting vocal-house-style instrumental led by tenor sax, with strings and electric piano",
        "a driving tech house groove with woodblock, pizzicato strings and a pumping bass",
        "a soaring progressive house ride with nylon guitar and flute over an endless summer horizon"]
SLOTS = ["2026-10-22T23:55:00", "2026-10-23T05:55:00", "2026-10-23T23:55:00", "2026-10-24T05:55:00", "2026-10-24T23:55:00",
         "2026-10-25T05:55:00", "2026-10-25T23:55:00", "2026-10-26T05:55:00", "2026-10-26T23:55:00", "2026-10-27T05:55:00"]
out = []
for i, h in enumerate(H):
    m = json.load(open(f'/tmp/mirage/out/{i+1:02d}.meta.json')); b = h['brief']; fmt = 'video' if i % 2 == 0 else 'short'
    import sys; sys.path.insert(0, '/home/claude/videosyndication/djvelvetgrey/v2'); import styles as S
    label = S.STYLES[b['style']]['label'].replace(' (Instrumental)', '')
    tag = {'disco': '#disco #discohouse', 'nudisco': '#nudisco #discohouse', 'afro': '#afrohouse #afrobeats', 'deep': '#deephouse #chillhouse',
           'melodic': '#melodichouse #chillout', 'tropical': '#tropicalhouse #summervibes', 'house': '#housemusic #pianohouse',
           'vocal': '#vocalhouse #housemusic', 'tech': '#techhouse #clubmusic', 'progressive': '#progressivehouse #summermusic'}[b['style']]
    title = h['title']; ph, pg = PH[i]
    text = (f"{title} by DJ Velvet Purple is {MOOD[i]}.\n\nInstrumental. Key: {m['key']}, {b['bpm']} BPM.\n\n"
            f"Photo: {ph} on Unsplash - {pg}\nMusic: DJ Velvet Purple\nLabel: Mirage Tropical Records\n\n{tag} #instrumental #DJVelvetPurple #MirageTropicalRecords"
            + (" #shorts" if fmt == 'short' else ''))
    yt_title = f"{title} - DJ Velvet Purple | {label} Instrumental" + (" #shorts" if fmt == 'short' else '')
    tags = [label.lower(), 'instrumental', 'house music', 'DJ Velvet Purple', 'Mirage Tropical Records', title, 'beach music', 'summer vibes', 'tropical', m['key']]
    out.append({'n': i + 1, 'release': f'mtr{i+1:03d}', 'title': title, 'format': fmt, 'slot': SLOTS[i], 'text': text, 'yt_title': yt_title, 'tags': tags,
                'photographer': ph, 'photo_page': pg, 'style': b['style'], 'key': m['key'], 'bpm': b['bpm']})
json.dump(out, open('/tmp/mirage/posts.json', 'w'), indent=1)
for o in out: print(o['release'], o['format'], o['slot'], o['yt_title'], len(o['yt_title']))
