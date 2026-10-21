"""Marco Reyes's studio, drawn as layered SVG (viewBox 1600x900).

Layers, back to front: bg (room + chair), body, head (animated: mouth/eyes),
desk (front furniture), hands (rest / point).  Marco sits at x=600.
"""
import random

VB = (1600, 900)
HEAD_PIVOT = (600, 445)       # head rotates around the chin/collar
HEAD_BOX = (470, 225, 730, 470)

DEFS = """<defs>
<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3F2C22"/><stop offset="1" stop-color="#271A13"/></linearGradient>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16244A"/><stop offset="0.7" stop-color="#2B3F6E"/><stop offset="1" stop-color="#5A4A6A"/></linearGradient>
<radialGradient id="moon" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#FFF6D8"/><stop offset="0.6" stop-color="#F3E3B0"/><stop offset="1" stop-color="#F3E3B0" stop-opacity="0"/></radialGradient>
<linearGradient id="curtain" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#4A1418"/><stop offset="0.25" stop-color="#7E2228"/><stop offset="0.5" stop-color="#5A181C"/><stop offset="0.75" stop-color="#8A2A2E"/><stop offset="1" stop-color="#4A1418"/></linearGradient>
<linearGradient id="wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9A6A42"/><stop offset="1" stop-color="#6E4A2E"/></linearGradient>
<linearGradient id="deskfront" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6A452A"/><stop offset="1" stop-color="#3E2817"/></linearGradient>
<linearGradient id="leather" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#4A1C16"/><stop offset="0.5" stop-color="#7A3222"/><stop offset="1" stop-color="#4A1C16"/></linearGradient>
<linearGradient id="cardigan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#22382C"/><stop offset="0.5" stop-color="#3C5E48"/><stop offset="1" stop-color="#22382C"/></linearGradient>
<radialGradient id="skin" cx="0.42" cy="0.38" r="0.7"><stop offset="0" stop-color="#EDB98F"/><stop offset="0.7" stop-color="#D49A6E"/><stop offset="1" stop-color="#B57A52"/></radialGradient>
<radialGradient id="nose" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stop-color="#EBA582"/><stop offset="1" stop-color="#BF7652"/></radialGradient>
<linearGradient id="stache" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#D9D4CC"/></linearGradient>
<linearGradient id="chrome" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6E7480"/><stop offset="0.35" stop-color="#E9EDF2"/><stop offset="0.6" stop-color="#9BA2AE"/><stop offset="1" stop-color="#4C525C"/></linearGradient>
<radialGradient id="glow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#FFD58A" stop-opacity="0.55"/><stop offset="1" stop-color="#FFD58A" stop-opacity="0"/></radialGradient>
<radialGradient id="spot" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#FFE2B0" stop-opacity="0.22"/><stop offset="1" stop-color="#FFE2B0" stop-opacity="0"/></radialGradient>
<radialGradient id="vignette" cx="0.5" cy="0.45" r="0.75"><stop offset="0.55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.55"/></radialGradient>
<linearGradient id="greenglass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3E8A5A"/><stop offset="1" stop-color="#1E5034"/></linearGradient>
</defs>"""


def _svg(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VB[0]} {VB[1]}" width="{VB[0]}" height="{VB[1]}">{DEFS}{body}</svg>'


def bg():
    r = random.Random(11)
    p = ['<rect width="1600" height="900" fill="url(#wall)"/>']
    p += [f'<rect x="{x}" y="30" width="18" height="540" fill="#FFFFFF" fill-opacity="0.025"/>' for x in range(0, 1600, 44)]
    p.append('<rect y="0" width="1600" height="34" fill="#2A1C14"/><rect y="34" width="1600" height="6" fill="#8A6A42"/>')
    # window with night skyline
    p.append('<rect x="380" y="60" width="440" height="420" fill="#5A3A24"/>')
    p.append('<rect x="398" y="78" width="404" height="384" fill="url(#sky)"/>')
    for _ in range(40):
        p.append(f'<circle cx="{r.uniform(400,800):.0f}" cy="{r.uniform(82,250):.0f}" r="{r.uniform(0.8,2):.1f}" fill="#FFFFFF" fill-opacity="{r.uniform(.4,.9):.2f}"/>')
    p.append('<circle cx="720" cy="150" r="70" fill="url(#moon)" opacity="0.5"/><circle cx="720" cy="150" r="30" fill="#F7EBC6"/>'
             '<circle cx="710" cy="142" r="6" fill="#E6D7A8"/><circle cx="728" cy="160" r="4" fill="#E6D7A8"/>')
    x = 398
    while x < 802:
        w = r.randint(28, 60); h = r.randint(70, 210); top = 462 - h
        col = r.choice(["#121B33", "#17213D", "#0F172C"])
        p.append(f'<rect x="{x}" y="{top}" width="{min(w, 802 - x)}" height="{h}" fill="{col}"/>')
        for wy in range(top + 10, 452, 16):
            for wx in range(x + 6, min(x + w, 802) - 6, 12):
                if r.random() < 0.38:
                    p.append(f'<rect x="{wx}" y="{wy}" width="5" height="7" fill="#FFD27A" fill-opacity="{r.uniform(.5,.95):.2f}"/>')
        x += w + r.randint(0, 6)
    p.append('<rect x="596" y="78" width="8" height="384" fill="#5A3A24"/><rect x="398" y="266" width="404" height="8" fill="#5A3A24"/>')
    p.append('<rect x="366" y="470" width="468" height="18" rx="3" fill="#8A6A42"/>')
    # curtains
    p.append('<path d="M330,44 L430,44 C420,200 440,400 410,620 L330,620 Z" fill="url(#curtain)"/>')
    p.append('<path d="M870,44 L770,44 C780,200 760,400 790,620 L870,620 Z" fill="url(#curtain)"/>')
    p.append('<rect x="320" y="40" width="560" height="26" rx="6" fill="#5A181C"/><rect x="310" y="36" width="580" height="8" rx="4" fill="#C9962E"/>')
    # left: framed painting, floor lamp, plant
    p.append('<rect x="80" y="110" width="210" height="160" fill="#B8862E"/><rect x="94" y="124" width="182" height="132" fill="#F0B070"/>'
             '<circle cx="230" cy="190" r="22" fill="#FFE4A0"/><path d="M94,256 L94,210 Q140,170 190,215 Q230,190 276,220 L276,256 Z" fill="#6A7A3A"/>'
             '<path d="M94,256 L94,236 Q160,212 276,240 L276,256 Z" fill="#4A5A2A"/>')
    # wainscoting
    p.append('<rect y="560" width="1600" height="340" fill="#2E1E14"/><rect y="556" width="1600" height="10" fill="#7A5A3A"/>')
    for px in range(20, 1600, 200):
        p.append(f'<rect x="{px}" y="590" width="170" height="260" rx="4" fill="none" stroke="#4A3220" stroke-width="4"/>')
    # bookshelf
    p.append('<rect x="990" y="70" width="580" height="660" fill="#4A3020"/><rect x="1006" y="86" width="548" height="628" fill="#24170F"/>')
    shelves = [86, 216, 346, 476, 606]
    colors = ["#7A2E22", "#2E4A6A", "#C9962E", "#3E5A3A", "#8A5A3A", "#5A2E4A", "#A84A2A", "#D9C9A0", "#2A3A4A", "#6A6A3A"]
    for si, sy in enumerate(shelves[:-1]):
        base = shelves[si + 1]
        x = 1012
        while x < 1540:
            if r.random() < 0.08 and x < 1470:
                if si == 1:
                    p.append(f'<circle cx="{x+34}" cy="{base-50}" r="34" fill="#3A6A8A"/><path d="M{x+14},{base-70} q20,10 40,-6 M{x+10},{base-44} q30,8 50,-2" stroke="#6A9A5A" stroke-width="8" fill="none"/>'
                             f'<rect x="{x+28}" y="{base-14}" width="12" height="14" fill="#C9962E"/>')
                    x += 76; continue
                if si == 2:
                    p.append(f'<path d="M{x+12},{base-90} h40 v14 q0,26 -20,30 q-20,-4 -20,-30 z" fill="#D9B45A"/><rect x="{x+26}" y="{base-46}" width="12" height="30" fill="#D9B45A"/><rect x="{x+14}" y="{base-18}" width="36" height="18" fill="#8A6A2A"/>')
                    x += 70; continue
            w = r.randint(14, 30); h = r.randint(78, 116); c = r.choice(colors)
            if r.random() < 0.07:
                p.append(f'<rect x="{x+10}" y="{base-h}" width="{w}" height="{h}" fill="{c}" transform="rotate(12 {x+10} {base})"/>')
                x += w + 26; continue
            p.append(f'<rect x="{x}" y="{base-h}" width="{w}" height="{h}" fill="{c}"/>'
                     f'<rect x="{x}" y="{base-h+12}" width="{w}" height="4" fill="#E9D9A8" fill-opacity="0.55"/>'
                     f'<rect x="{x}" y="{base-24}" width="{w}" height="3" fill="#E9D9A8" fill-opacity="0.45"/>')
            x += w + r.randint(1, 3)
        p.append(f'<rect x="1006" y="{base}" width="548" height="14" fill="#5A3A24"/>')
    p.append('<rect x="990" y="70" width="580" height="16" fill="#6A4A2E"/>')
    # soft light behind Marco
    p.append('<ellipse cx="600" cy="380" rx="420" ry="330" fill="url(#spot)"/>')
    # wingback chair
    p.append('<path d="M420,620 L420,330 C420,270 440,240 470,232 C470,180 520,160 600,160 C680,160 730,180 730,232 C760,240 780,270 780,330 L780,620 Z" fill="url(#leather)"/>')
    p.append('<path d="M420,330 C420,280 440,250 470,240 L470,620 L420,620 Z" fill="#5A2418" fill-opacity="0.6"/>'
             '<path d="M780,330 C780,280 760,250 730,240 L730,620 L780,620 Z" fill="#5A2418" fill-opacity="0.6"/>')
    for ty in range(200, 600, 46):
        for tx in range(490, 720, 46):
            p.append(f'<circle cx="{tx + (23 if (ty // 46) % 2 else 0)}" cy="{ty}" r="4" fill="#3A140E"/>')
    p.append('<path d="M470,232 C470,180 520,160 600,160 C680,160 730,180 730,232" stroke="#C9962E" stroke-width="3" stroke-dasharray="2 9" fill="none"/>')
    return _svg("".join(p))


def body():
    return _svg(
        '<circle cx="600" cy="452" r="34" fill="#C68A60"/>'
        '<path d="M370,700 C360,560 420,468 560,450 L640,450 C780,468 840,560 830,700 Z" fill="url(#cardigan)"/>'
        '<path d="M560,452 L640,452 L615,640 L585,640 Z" fill="#F4F1EA"/>'
        '<path d="M560,452 L600,500 L586,640 L548,640 Z" fill="#30503C"/><path d="M640,452 L600,500 L614,640 L652,640 Z" fill="#30503C"/>'
        '<circle cx="600" cy="540" r="5" fill="#D9B45A"/><circle cx="600" cy="582" r="5" fill="#D9B45A"/><circle cx="600" cy="624" r="5" fill="#D9B45A"/>'
        '<path d="M572,448 L600,476 L586,486 Z" fill="#FFFFFF"/><path d="M628,448 L600,476 L614,486 Z" fill="#FFFFFF"/>'
        '<path d="M558,456 L598,474 L558,494 Q550,475 558,456 Z" fill="#C8202A"/><path d="M642,456 L602,474 L642,494 Q650,475 642,456 Z" fill="#C8202A"/>'
        '<rect x="589" y="464" width="22" height="20" rx="5" fill="#A51C24"/>'
        '<circle cx="572" cy="468" r="2.6" fill="#F4F1EA"/><circle cx="566" cy="482" r="2.6" fill="#F4F1EA"/><circle cx="630" cy="470" r="2.6" fill="#F4F1EA"/><circle cx="634" cy="484" r="2.6" fill="#F4F1EA"/>'
    )


MOUTHS = [
    '<path d="M578,418 Q600,434 622,418" stroke="#6A2E22" stroke-width="4.5" fill="none" stroke-linecap="round"/>',
    '<ellipse cx="600" cy="422" rx="17" ry="8" fill="#5A1E18"/><ellipse cx="600" cy="426" rx="9" ry="3" fill="#C8605A"/>',
    '<ellipse cx="600" cy="424" rx="20" ry="15" fill="#5A1E18"/><rect x="586" y="410" width="28" height="6" rx="3" fill="#FFFFFF"/><ellipse cx="600" cy="433" rx="11" ry="5" fill="#C8605A"/>',
]
EYES = [
    ('<ellipse cx="568" cy="344" rx="12" ry="13" fill="#FFFFFF"/><ellipse cx="632" cy="344" rx="12" ry="13" fill="#FFFFFF"/>'
     '<circle cx="570" cy="346" r="8" fill="#5A3A22"/><circle cx="630" cy="346" r="8" fill="#5A3A22"/>'
     '<circle cx="570" cy="346" r="4.2" fill="#141010"/><circle cx="630" cy="346" r="4.2" fill="#141010"/>'
     '<circle cx="573" cy="342" r="2.4" fill="#FFFFFF"/><circle cx="633" cy="342" r="2.4" fill="#FFFFFF"/>'
     '<path d="M555,338 Q568,328 581,338 M619,338 Q632,328 645,338" stroke="#7A4A32" stroke-width="3" fill="none" stroke-linecap="round"/>'),
    '<path d="M555,346 Q568,352 581,346 M619,346 Q632,352 645,346" stroke="#4A2A1A" stroke-width="3.5" fill="none" stroke-linecap="round"/>',
]


def head(mouth=0, eyes=0):
    stache_l = 'M600,398 C588,388 566,386 548,394 C530,402 520,398 516,384 C512,372 518,364 526,366 C520,376 528,386 540,380 C560,370 586,372 600,384 Z'
    return _svg(
        '<ellipse cx="497" cy="352" rx="16" ry="25" fill="#C68A60"/><ellipse cx="703" cy="352" rx="16" ry="25" fill="#C68A60"/>'
        '<ellipse cx="499" cy="352" rx="7" ry="13" fill="#A86E48"/><ellipse cx="701" cy="352" rx="7" ry="13" fill="#A86E48"/>'
        '<ellipse cx="600" cy="345" rx="102" ry="104" fill="url(#skin)"/>'
        '<ellipse cx="572" cy="262" rx="34" ry="14" fill="#FFF0DC" fill-opacity="0.45" transform="rotate(-12 572 262)"/>'
        # white side hair
        '<path d="M500,330 C494,300 506,282 520,276 C514,296 518,312 528,322 C512,320 506,338 512,352 C500,348 498,340 500,330 Z" fill="#EDEAE4"/>'
        '<path d="M700,330 C706,300 694,282 680,276 C686,296 682,312 672,322 C688,320 694,338 688,352 C700,348 702,340 700,330 Z" fill="#EDEAE4"/>'
        # glasses parked on the head
        '<path d="M520,292 Q540,284 548,284 M652,284 Q660,284 680,292" stroke="#B8902E" stroke-width="4" fill="none"/>'
        '<circle cx="572" cy="282" r="24" fill="#BFE0F0" fill-opacity="0.35" stroke="#D9B45A" stroke-width="5"/>'
        '<circle cx="628" cy="282" r="24" fill="#BFE0F0" fill-opacity="0.35" stroke="#D9B45A" stroke-width="5"/>'
        '<path d="M596,280 Q600,274 604,280" stroke="#D9B45A" stroke-width="5" fill="none"/>'
        '<path d="M560,272 l10,-6 M616,272 l10,-6" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" opacity="0.8"/>'
        # eyebrows
        '<path d="M548,322 Q566,308 588,318" stroke="#F4F1EA" stroke-width="10" fill="none" stroke-linecap="round"/>'
        '<path d="M612,318 Q634,308 652,322" stroke="#F4F1EA" stroke-width="10" fill="none" stroke-linecap="round"/>'
        + EYES[eyes] +
        '<circle cx="546" cy="384" r="17" fill="#E8836A" fill-opacity="0.35"/><circle cx="654" cy="384" r="17" fill="#E8836A" fill-opacity="0.35"/>'
        + MOUTHS[mouth] +
        '<path d="M584,440 Q600,448 616,440" stroke="#B57A52" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.7"/>'
        f'<path d="{stache_l}" fill="url(#stache)" stroke="#CFC9C0" stroke-width="1.5"/>'
        f'<path d="{stache_l}" fill="url(#stache)" stroke="#CFC9C0" stroke-width="1.5" transform="translate(1200,0) scale(-1,1)"/>'
        '<ellipse cx="600" cy="372" rx="22" ry="19" fill="url(#nose)"/><ellipse cx="593" cy="365" rx="7" ry="4.5" fill="#FFFFFF" fill-opacity="0.45"/>'
    )


def desk():
    return _svg(
        '<path d="M1,900 L1,720 C10,700 30,690 50,700 L110,700 L120,900 Z" fill="#8A4A2A"/>'
        '<path d="M40,700 C10,620 30,560 60,540 C50,600 70,640 70,700 Z M80,700 C80,620 110,560 150,560 C120,600 110,650 100,700 Z M60,700 C50,640 80,600 110,610 C90,640 80,670 78,700 Z" fill="#2F6A3A"/>'
        '<rect x="110" y="626" width="980" height="30" rx="8" fill="url(#wood)"/>'
        '<rect x="126" y="656" width="948" height="244" fill="url(#deskfront)"/>'
        '<rect x="160" y="690" width="300" height="170" rx="6" fill="none" stroke="#2E1C10" stroke-width="5"/>'
        '<rect x="740" y="690" width="300" height="170" rx="6" fill="none" stroke="#2E1C10" stroke-width="5"/>'
        '<rect x="285" y="768" width="50" height="10" rx="5" fill="#C9962E"/><rect x="865" y="768" width="50" height="10" rx="5" fill="#C9962E"/>'
        '<rect x="540" y="728" width="120" height="64" rx="8" fill="#2A1A10" stroke="#C9962E" stroke-width="3"/>'
        '<text x="590" y="774" text-anchor="middle" font-family="Source Serif 4, serif" font-size="38" font-weight="700" fill="#D9B45A">GN</text>'
        '<circle cx="632" cy="768" r="6" fill="#D7262E"/>'
        # banker's lamp
        '<ellipse cx="230" cy="560" rx="150" ry="70" fill="url(#glow)"/>'
        '<ellipse cx="230" cy="626" rx="46" ry="9" fill="#C9962E"/><rect x="226" y="560" width="8" height="66" fill="#C9962E"/>'
        '<path d="M160,566 Q230,520 300,566 Z" fill="url(#greenglass)"/><rect x="160" y="564" width="140" height="6" rx="3" fill="#FFE6A0"/>'
        # books + mug
        '<rect x="900" y="604" width="150" height="22" rx="3" fill="#2E4A6A"/><rect x="910" y="584" width="130" height="20" rx="3" fill="#7A2E22"/><rect x="904" y="566" width="140" height="18" rx="3" fill="#C9962E"/>'
        '<rect x="840" y="580" width="40" height="46" rx="6" fill="#F4F1EA"/><path d="M880,592 q16,0 16,12 q0,12 -16,12" stroke="#F4F1EA" stroke-width="6" fill="none"/>'
        '<path d="M852,572 q-6,-12 4,-22 M866,572 q-6,-12 4,-22" stroke="#FFFFFF" stroke-opacity="0.35" stroke-width="3" fill="none"/>'
        # vintage microphone
        '<ellipse cx="800" cy="626" rx="34" ry="8" fill="#3A3F48"/><rect x="796" y="520" width="8" height="106" fill="url(#chrome)"/>'
        '<path d="M786,530 L814,530 L808,512 L792,512 Z" fill="#3A3F48"/>'
        '<rect x="768" y="420" width="64" height="96" rx="30" fill="url(#chrome)"/>'
        '<path d="M774,446 H826 M772,462 H828 M772,478 H828 M774,494 H826" stroke="#5A606A" stroke-width="2.5"/>'
        '<rect x="764" y="462" width="72" height="12" rx="4" fill="#2A2E36"/>'
    )


def hands(mode=0):
    arm = 'stroke="#30503C" stroke-width="58" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    cuff = 'stroke="#F4F1EA" stroke-width="8" fill="none" stroke-linecap="round"'
    right = (f'<path d="M752,500 C800,560 790,612 722,622 L668,622" {arm}/>'
             '<ellipse cx="640" cy="624" rx="34" ry="20" fill="#D49A6E"/><path d="M620,628 h40 M624,637 h34" stroke="#B57A52" stroke-width="2.5"/>')
    if mode == 0:
        return _svg(f'<path d="M448,500 C400,560 410,612 478,622 L532,622" {arm}/>'
                    '<ellipse cx="562" cy="626" rx="34" ry="20" fill="#D49A6E"/><path d="M542,630 h40 M546,639 h34" stroke="#B57A52" stroke-width="2.5"/>'
                    + right)
    return _svg(f'<path d="M450,500 L402,572 L446,452" {arm}/>'
                f'<path d="M432,456 L466,466" {cuff}/>'
                '<g transform="rotate(-10 452 430)">'
                '<rect x="430" y="398" width="46" height="50" rx="18" fill="#D49A6E"/>'
                '<rect x="430" y="356" width="12" height="50" rx="6" fill="#D49A6E" transform="rotate(-10 436 404)"/>'
                '<rect x="443" y="348" width="12" height="56" rx="6" fill="#D49A6E" transform="rotate(-3 449 404)"/>'
                '<rect x="456" y="350" width="12" height="54" rx="6" fill="#D49A6E" transform="rotate(4 462 404)"/>'
                '<rect x="468" y="362" width="11" height="44" rx="5.5" fill="#D49A6E" transform="rotate(11 473 404)"/>'
                '<rect x="424" y="398" width="13" height="38" rx="6.5" fill="#D49A6E" transform="rotate(-38 432 432)"/>'
                '<path d="M440,430 q12,6 26,0" stroke="#B57A52" stroke-width="2.5" fill="none"/>'
                '</g>'
                + right)
