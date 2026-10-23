"""YouTube title, description and tags for a DJ Velvet Purple release, laid out like the most-viewed uploads on big
house/disco channels: artist - title at the top, a short hook line, subscribe call, track details, photo credit, a
"perfect for" keyword line and hashtags. The photo credit lives here only (never drawn on the video).
Nothing here may mention AI.

    python3 mirage/describe.py --title T --style afro --key "C minor" --bpm 121 --format video|short \
        --mood "one line on the mood and instruments" --photographer NAME --photo-page URL
"""
import argparse, json

GENRE = {'disco': 'Disco', 'nudisco': 'Nu-Disco', 'afro': 'Afro House', 'deep': 'Deep House', 'melodic': 'Melodic House',
         'tropical': 'Tropical House', 'house': 'House', 'vocal': 'Vocal House', 'tech': 'Tech House', 'progressive': 'Progressive House',
         'chill': 'Chill House', 'french': 'French House', 'funky': 'Funky House', 'soulful': 'Soulful House', 'organic': 'Organic House'}
TAGS = {'disco': ['disco', 'discohouse', 'funkydisco'], 'nudisco': ['nudisco', 'discohouse', 'indiedance'],
        'afro': ['afrohouse', 'afrobeats', 'amapiano'], 'deep': ['deephouse', 'chillhouse', 'lofihouse'],
        'melodic': ['melodichouse', 'melodictechno', 'chillout'], 'tropical': ['tropicalhouse', 'summervibes', 'beachhouse'],
        'house': ['housemusic', 'pianohouse', 'classichouse'], 'vocal': ['vocalhouse', 'housemusic', 'soulfulhouse'],
        'tech': ['techhouse', 'clubmusic', 'minimalhouse'], 'progressive': ['progressivehouse', 'summermusic', 'edm'],
        'soulful': ['soulfulhouse', 'deephouse', 'housemusic'], 'french': ['frenchhouse', 'filterhouse', 'discohouse']}
USES = {'disco': 'sunset drives, rooftop parties and dancing at home', 'nudisco': 'late-night drives, city lights and dance floors',
        'afro': 'beach parties, workouts and sunset sessions', 'deep': 'pool days, night swims, studying and relaxing',
        'melodic': 'road trips, sunsets and focus sessions', 'tropical': 'beach days, pool parties and summer mornings',
        'house': 'rooftop afternoons, workouts and pre-party', 'vocal': 'summer parties, gym sessions and good-mood days',
        'tech': 'club nights, gym sessions and driving', 'progressive': 'festival sunsets, road trips and running',
        'soulful': 'golden-hour drives, Sunday sessions and dinner parties', 'french': 'late-night drives, house parties and dancing'}


PHOTO_TAG = {'bikini': 'bikini beach', 'fashion': 'summer fashion', 'nature': 'tropical scenery'}


def make(title, style, key, bpm, fmt, mood, photographer, photo_page, photo_kind='bikini'):
    g = GENRE.get(style, style.title()); short = fmt == 'short'
    yt_title = f'{title} - DJ Velvet Purple | {g} Instrumental' + (' #shorts' if short else '')
    tags = TAGS.get(style, [g.lower().replace(' ', '').replace('-', '')])
    hashtags = ' '.join('#' + t for t in tags + ['instrumental', 'summermix', 'DJVelvetPurple', 'MirageTropicalRecords'] + (['shorts'] if short else []))
    text = '\n'.join([
        f'🎧 DJ Velvet Purple - {title} ({g} Instrumental)',
        '',
        mood,
        '',
        f'🔔 Subscribe to Mirage Tropical Records for new {g.lower()} every day, and tap the bell so you never miss a drop.',
        '👍 Like, comment and share if this one hits.',
        '',
        f'🎵 Track: {title}',
        '🎤 Artist: DJ Velvet Purple',
        '💿 Label: Mirage Tropical Records',
        f'🎚 Genre: {g} (Instrumental)',
        f'🎹 Key: {key} · {bpm} BPM',
        '',
        f'📸 Photo: {photographer} on Unsplash - {photo_page}',
        '',
        f'{g} for {USES.get(style, "summer days, parties and chill sessions")}. Beach vibes, summer mix, '
        f'{g.lower()} {"short" if short else "music"} 2026.',
        '',
        hashtags])
    tag_list = [g.lower(), f'{g.lower()} instrumental', f'{g.lower()} 2026', 'instrumental', 'house music', 'summer mix', 'beach vibes',
                'DJ Velvet Purple', 'Mirage Tropical Records', title, f'DJ Velvet Purple {title}', PHOTO_TAG.get(photo_kind, 'summer vibes'), 'summer vibes', key]
    return {'yt_title': yt_title, 'description': text, 'tags': tag_list}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    for k in ('title', 'style', 'key', 'bpm', 'mood', 'photographer', 'photo-page'): ap.add_argument('--' + k, required=True)
    ap.add_argument('--format', choices=['video', 'short'], default='video')
    ap.add_argument('--photo-kind', choices=['bikini', 'fashion', 'nature'], default='bikini')
    a = ap.parse_args()
    print(json.dumps(make(a.title, a.style, a.key, a.bpm, a.format, a.mood, a.photographer, a.photo_page, a.photo_kind), indent=1, ensure_ascii=False))
