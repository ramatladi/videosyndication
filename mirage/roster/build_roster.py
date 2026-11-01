"""Build mirage/artists.json: the Mirage Tropical Records roster (Sello, 1 Nov 2026: "add more DJs and artists up to
1000, representing male/female and ethnicities").

    python3 mirage/roster/build_roster.py            # rewrites mirage/artists.json (deterministic, seed 1101)

Every act is fictional. Each has a gender (female / male for solo acts and DJs; female, male or mixed for duos and
collectives) and a heritage: the cultural origin of the given names it uses (a name heritage, not a claim about
anyone's ethnicity). Acts are spread evenly over the 15 sub-genres, and every sub-genre gets the same balance of
genders and a spread of heritages, so no heritage is tied to a style (no "African names only in afro").
The 15 original acts stay first in their style's roster.
Names stay <= 20 characters (they are letter-spaced on the video's brand pill) and use Latin letters only.
"""
import json, os, random, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'artists.json')
TOTAL = 1000

# given names by heritage: (female, male, surnames). Common, real given names; surnames are used sparingly.
H = {
 'West African (Nigeria)': ('Adaeze Amara Chiamaka Ifeoma Ngozi Temi Funmi Yewande Zainab Halima Bisola Ebele',
                            'Chidi Emeka Tunde Femi Obinna Seun Kelechi Dayo Ike Nnamdi Bayo Uche',
                            'Okafor Adeyemi Nwosu Balogun Eze Okoro'),
 'West African (Ghana)': ('Ama Akosua Efua Abena Adwoa Esi Afia Yaa Naana Dzifa',
                          'Kofi Kwame Kojo Yaw Kwesi Kwabena Ekow Nana Fiifi Selasi',
                          'Mensah Owusu Boateng Asante Ofori'),
 'West African (Senegal/Mali)': ('Awa Fatou Aminata Mariama Coumba Aissatou Ndeye Kadiatou',
                                 'Moussa Ousmane Mamadou Cheikh Ibrahima Babacar Seydou Lamine',
                                 'Diallo Ndiaye Traore Sow Keita'),
 'East African (Kenya/Tanzania)': ('Wanjiru Achieng Njeri Akinyi Zawadi Imani Nyokabi Wambui Neema Halima',
                                   'Otieno Kamau Baraka Juma Mwangi Omondi Jabari Tumaini Kiprono Rashidi',
                                   'Odhiambo Kariuki Wanyama Mutua'),
 'East African (Ethiopia)': ('Selam Hiwot Meron Liya Tigist Bethlehem Saba Mahlet',
                             'Dawit Yonas Abel Bereket Henok Tesfaye Elias Nahom',
                             'Tadesse Bekele Haile Girma'),
 'Southern African (Zulu/Xhosa)': ('Thandiwe Nomvula Zanele Lindiwe Ayanda Nandi Buhle Sindisiwe Zodwa Nolwazi',
                                   'Sipho Thabo Lwazi Mandla Siyabonga Bongani Themba Lungile Andile Sizwe',
                                   'Dlamini Ndlovu Mkhize Zulu Khumalo Mthembu'),
 'Southern African (Sotho/Tswana/Pedi)': ('Lerato Palesa Mpho Dineo Boitumelo Kamogelo Refilwe Tshegofatso Masego Karabo',
                                          'Tumelo Kagiso Lesego Tebogo Katlego Thapelo Neo Teboho Lehlohonolo Kgosi',
                                          'Mokoena Molefe Mahlangu Maseko Nkosi'),
 'Southern African (Afrikaans/Cape)': ('Anri Lize Mieke Elna Karlien Riana Zelda Chanel',
                                       'Pieter Johan Ruan Wian Stefan Danie Jaco Marius',
                                       'Botha Pretorius Venter Jacobs Adams'),
 'North African (Morocco/Algeria)': ('Yasmine Salma Imane Nadia Leila Samira Houda Meriem',
                                     'Youssef Karim Mehdi Anas Rachid Nabil Amine Hamza',
                                     'Benali Haddad El Idrissi Mansouri'),
 'Egyptian': ('Nour Mariam Farida Habiba Dina Reem Malak Jana',
              'Omar Tarek Karim Mostafa Hassan Ziad Adham Yassin',
              'Fahmy Mansour Saleh Naguib'),
 'Caribbean (Jamaica)': ('Shanice Kerrian Tanisha Marcia Kimone Jodi-Ann Shellene Toni',
                         'Andre Delroy Jermaine Kemar Rohan Damion Leroy Omari',
                         'Campbell Brown Grant Bailey Morgan'),
 'Caribbean (Trinidad/Barbados)': ('Kezia Anya Shivani Renee Kerisha Alana Tricia Simone',
                                   'Kerwin Rondell Machel Akeem Shane Jabari Darren Nikolai',
                                   'Ramdass Charles Joseph Khan Phillip'),
 'Haitian': ('Fabienne Nadège Mirlande Stéphanie Widline Guerda Rose-Marie Nathalie',
             'Jean-Paul Wyclef Ricardo Fritz Jocelyn Emmanuel Gérald Patrick',
             'Pierre Jean-Baptiste Desir Louis'),
 'Cuban/Dominican/Puerto Rican': ('Yamilé Marisol Yanet Xiomara Dayana Liset Mariela Yesenia Lourdes Nayeli',
                                  'Yoandri Rafael Yunior Ramón Alexis Luis Ángel Osvaldo Héctor Javier',
                                  'Batista Delgado Rosario Pérez Santana'),
 'Brazilian': ('Luana Beatriz Juliana Camila Larissa Thais Bianca Rafaela Iara Jaqueline',
               'Thiago Rafael Lucas Caio Gabriel Rodrigo Diego Mateus Bruno Vinícius',
               'Souza Oliveira Lima Barros Nogueira Teixeira'),
 'Colombian/Venezuelan': ('Valentina Daniela Catalina Mariana Paola Juliana Natalia Isabela',
                          'Santiago Andrés Camilo Sebastián Julián Felipe Mateo Esteban',
                          'Restrepo Cárdenas Ospina Rojas'),
 'Mexican': ('Ximena Guadalupe Fernanda Regina Itzel Citlali Paloma Mariana Renata Andrea',
             'Diego Emiliano Alejandro Rodrigo Iker Leonardo Joaquín Mauricio Arturo Rubén',
             'Hernández Ramírez Villarreal Castañeda Ochoa'),
 'Argentine/Chilean': ('Florencia Agustina Josefina Delfina Antonella Martina Camila Lucía',
                       'Facundo Joaquín Matías Tomás Nicolás Ignacio Gonzalo Lautaro',
                       'Ferreyra Acosta Bustos Etchegaray'),
 'African American': ('Aaliyah Jasmine Imani Kiara Tasha Destiny Nia Jada Keisha Monique Ebony Danielle',
                      'Darnell Marcus Terrence Andre Malik Jamal DeShawn Tyrone Isaiah Xavier Jerome Cedric',
                      'Washington Jefferson Banks Freeman Brooks'),
 'Anglo American/Canadian': ('Brooke Hailey Madison Kelsey Megan Lauren Taylor Paige Morgan Shelby',
                             'Tyler Cody Dustin Kyle Logan Travis Garrett Wesley Colton Bryce',
                             'Whitaker Callahan Mercer Holloway'),
 'British/Irish': ('Siobhan Niamh Imogen Harriet Ciara Freya Aoife Poppy Eleanor Maeve',
                   'Callum Rory Declan Alfie Ciaran Hamish Oisin Rhys Finley Gareth',
                   'Fitzgerald Ashworth Doyle Pemberton Gallagher'),
 'French/Belgian': ('Margaux Camille Léa Chloé Manon Inès Clémence Juliette Océane Élodie',
                    'Théo Hugo Bastien Mathis Julien Lucas Baptiste Antoine Rémi Étienne',
                    'Moreau Lefèvre Fontaine Girard Rousseau'),
 'Italian': ('Giulia Chiara Francesca Martina Alessia Bianca Elisa Serena Ilaria Sofia',
             'Lorenzo Matteo Alessandro Davide Federico Giacomo Luca Marco Riccardo Tommaso',
             'Romano Esposito Ferrara Bellini Conti'),
 'Spanish/Catalan': ('Lucía Carmen Paula Alba Nerea Ainhoa Marta Laia Irene Rocío',
                     'Pablo Álvaro Hugo Jordi Iván Marcos Sergio Unai Adrián Xavi',
                     'Navarro Serrano Puig Domínguez Ortega'),
 'Portuguese/Cape Verdean': ('Inês Mafalda Beatriz Leonor Carolina Matilde Djeneba Nelida',
                             'Tiago Duarte Rui Nuno Gonçalo Afonso Ilídio Kelvin',
                             'Fonseca Tavares Monteiro Semedo'),
 'German/Austrian/Swiss': ('Lena Hannah Johanna Katrin Mia Annika Theresa Leonie Franziska Greta',
                           'Lukas Felix Jonas Maximilian Tobias Moritz Florian Niklas Jannik Stefan',
                           'Becker Hoffmann Krüger Brandt Vogel'),
 'Dutch/Flemish': ('Sanne Lotte Femke Anouk Fleur Maartje Ilse Noor',
                   'Daan Sem Bram Jesse Thijs Ruben Joris Stijn',
                   'de Vries Visser Bakker Peeters'),
 'Nordic': ('Freja Saga Ingrid Linnea Astrid Sigrid Elin Maja Tuva Liv',
            'Mikkel Anders Erik Lars Henrik Oskar Viggo Magnus Emil Aksel',
            'Lindqvist Halvorsen Nyberg Sorensen Aalto'),
 'Greek/Cypriot': ('Eleni Katerina Despina Ioanna Sofia Dafni Myrto Zoe',
                   'Nikos Giorgos Kostas Yannis Stelios Thanos Alexis Petros',
                   'Papadakis Nikolaou Georgiou Vlachos'),
 'Polish/Czech/Slovak': ('Zofia Kasia Agnieszka Marta Natalia Tereza Klára Weronika',
                         'Kacper Jakub Tomasz Bartek Ondrej Michal Wojtek Filip',
                         'Nowak Kowalski Dvorak Wisniewski'),
 'Ukrainian/Baltic': ('Oksana Daryna Solomiya Iryna Laima Kristina Milda Viktoriya',
                      'Taras Bohdan Andriy Mykola Lukas Mantas Rasmus Ostap',
                      'Shevchenko Bondar Kalnins Petrauskas'),
 'Balkan': ('Jelena Mila Ivana Teodora Ana Marija Dunja Lejla',
            'Luka Marko Stefan Nikola Ivan Filip Emir Dino',
            'Petrovic Horvat Kovac Babic'),
 'Turkish': ('Elif Zeynep Ece Defne Selin Derya Melis Aylin',
             'Emre Kerem Mert Burak Can Deniz Baran Onur',
             'Yilmaz Demir Kaya Aydin'),
 'Lebanese/Levantine': ('Rania Maya Yara Lina Nadine Rasha Zeina Jana',
                        'Karim Rami Fadi Ziad Tarek Nadim Samir Elie',
                        'Haddad Khoury Nassar Saade'),
 'Persian': ('Shirin Parisa Leila Nazanin Mina Roya Golnar Setareh',
             'Arash Kian Darius Farhad Babak Reza Navid Kaveh',
             'Tehrani Ahmadi Farahani Rostami'),
 'Gulf Arab': ('Noura Mariam Hessa Alia Shamma Latifa Dana Reem',
               'Khalid Saif Rashid Faisal Majid Sultan Hamad Nasser',
               'Al Mansoori Al Suwaidi Al Kaabi'),
 'Indian (North)': ('Ananya Priya Ishita Kavya Aditi Meera Riya Simran Tanvi Neha',
                    'Arjun Rohan Kabir Vikram Aarav Rahul Aditya Karan Dev Ishaan',
                    'Malhotra Kapoor Verma Bhatia Saxena'),
 'Indian (South)': ('Lakshmi Divya Nithya Shruti Keerthana Anjali Revathi Swathi',
                    'Karthik Arvind Vishnu Pranav Siddharth Naveen Rajesh Suresh',
                    'Iyer Menon Reddy Nair Pillai'),
 'Pakistani/Bangladeshi': ('Ayesha Fatima Mehreen Sana Nusrat Farzana Hira Tahmina',
                           'Bilal Hamza Imran Faisal Rafiq Tanvir Zain Shahid',
                           'Qureshi Chowdhury Rahman Siddiqui'),
 'Sri Lankan/Nepali': ('Sanduni Dilini Nimali Anusha Pratima Sushmita Kalpana',
                       'Kasun Nuwan Dinesh Prabin Suman Roshan Bikash',
                       'Perera Fernando Gurung Shrestha'),
 'Japanese': ('Yuki Aiko Haruka Mei Sakura Rin Akane Emi Nanami Hana',
              'Haruto Kenji Ren Takumi Sora Daiki Riku Yuto Kaito Shun',
              'Takahashi Nakamura Fujii Mori Sato'),
 'Korean': ('Jiwoo Seoyeon Minji Haeun Yuna Soyeon Dahye Eunji',
            'Minho Jihoon Seojun Taeyang Hyunwoo Donghyun Junho Sungmin',
            'Kim Park Choi Kang Yoon'),
 'Chinese/Taiwanese': ('Mei Lin Xiao Wen Yuting Jia Hui Shu Fen Lan Qing',
                       'Wei Jun Hao Chen Bo Yu Ming Zhi Kai Long',
                       'Chen Lin Wang Huang Zhao'),
 'Filipino': ('Mariel Angelica Bea Kristine Joanna Pia Janelle Trixie',
              'Paolo Miguel Rafael Joaquin Marco Enzo Gabriel Andres',
              'Santos Reyes Dela Cruz Bautista Villanueva'),
 'Vietnamese': ('Linh Thao Mai Anh Huong Trang Ngoc Vy',
                'Minh Khoa Duc Bao Long Quang Huy Tuan',
                'Nguyen Tran Pham Le'),
 'Thai': ('Ploy Nok Fah Mint Ploypailin Pim Ying Kanya',
          'Krit Thanawat Arthit Nat Tan Phet Chai Somchai',
          'Srisai Wongsa Chaiyaphum'),
 'Indonesian/Malaysian': ('Ayu Dewi Putri Sari Nurul Intan Siti Melati',
                          'Arif Bayu Dimas Rizky Fajar Hafiz Iqbal Wira',
                          'Santoso Wijaya Rahman Hidayat'),
 'Pacific Islander (Samoan/Tongan/Fijian)': ('Leilani Malia Losa Mele Talia Seini Ana Vika',
                                            'Sione Tavita Iosefa Mosese Viliami Ratu Manu Tevita',
                                            'Tuilagi Fifita Vunipola'),
 'Maori': ('Aroha Mere Ataahua Hinewai Kahurangi Manaia Tui Ngaio',
           'Tama Rawiri Wiremu Nikau Tane Ihaia Kahu Rangi',
           'Ngata Parata Tamihana'),
 'Hawaiian': ('Malia Leilani Kalena Noelani Mahina Keala Pua Iolana',
              'Makoa Kekoa Kainoa Ikaika Keoni Kaleo Nalu Koa',
              'Kahale Kealoha Kanoho'),
 'Australian': ('Matilda Chelsea Brooke Jessica Tahlia Sienna Kirra Tegan',
                'Lachlan Brodie Jarrah Riley Mitchell Kai Jaxon Hamish',
                'Fletcher Lockwood Barrett'),
}

STAGE = """Tide Vane Meridian Honeywell Coast Harbour Lagoon Sundown Saltmarsh Palmer Riviera Calloway Moonfield Brightwater
Seabright Ember Amber Coral Laurel Haven Marlowe Solace Starling Kestrel Wren Fable Lumen Sable Ashby Hollis Bay
Linden Bloom Monsoon Sirocco Zephyr Rivers Stone Rains Skye Dune Shore Prism Glass Velvet Mirage Halcyon Solstice
Ferris Lark Corsair Atlas Echo Nova Vega Lyra Orion Juniper Maple Cedar Willow Saffron Indigo Cobalt Topaz Opal
Jade Garnet Ivory Silk Satin Linen Tango Cabana Pavilion Esplanade Promenade Marina Atoll Reef Isle Delta Bayou
Mesa Canyon Sierra Savanna Oasis Cascade Fjord Glacier Aurora Sol Luna Estrela Dusk Dawn Midnight Noon Daylight
Sunday Holiday Weekend Daydream Reverie Serenade Rhapsody Cadence Tempo Groove Rhythm Velour Neon Static Signal
Radio Cassette Vinyl Satellite Comet Ocelot Heron Falcon Swallow Pelican Flamingo Mango Guava Papaya Tamarind
Lychee Fig Citrus Lime Peach Cherry Honey Cocoa Vanilla Cinnamon Clove Pepper Basil Sage Mint Fern Moss Ivy""".split()

COLLECTIVE = ['Club', 'Society', 'Collective', 'Ensemble', 'Orchestra', 'Sound System', 'Players', 'Union', 'Assembly',
              'Express', 'Social', 'Lounge', 'Band', 'Quartet', 'Trio', 'Unit', 'Project', 'Crew', 'Syndicate', 'Brigade']
ADJ = """Golden Velvet Silver Coral Midnight Sunset Tropical Pastel Neon Crystal Amber Indigo Saffron Ivory Cobalt Jade
Lunar Solar Paper Satin Cosmic Electric Hazy Lazy Breezy Salty Sandy Starlit Moonlit Sunlit Twilight Copper
Emerald Ruby Magnolia Hibiscus Orchid Lotus Palm Mango Lime Peach Cherry Honey Cinnamon Vanilla""".split()
NOUN = """Harbour Lagoon Ferry Boulevard Avenue Terrace Pier Lido Cabana Atoll Reef Marina Lantern Kite Parade Carousel
Pavilion Veranda Courtyard Garden Orchard Palms Dunes Shores Islands Rivers Waves Tides Lights Signals Radios
Satellites Comets Flamingos Pelicans Herons Swallows Ocelots Tigers Panthers Jaguars Leopards Sparrows""".split()

STYLES = ['deep', 'melodic', 'house', 'afro', 'tropical', 'futurebass', 'nudisco', 'progressive', 'tech', 'trance', 'vocal',
          'soulful', 'disco', 'french', 'indiedance']
LINES = {
 'deep': ['late-night deep house', 'warm, dubby deep house grooves', 'smoky deep house with Rhodes and upright bass', 'after-hours deep house'],
 'melodic': ['melodic, organic house', 'melodic house with strings and woodwinds', 'cinematic melodic grooves', 'emotive melodic house'],
 'house': ['piano-driven sunshine house', 'feel-good house grooves', 'classic house piano and big basslines', 'summer house anthems'],
 'afro': ['afro house percussion and warm grooves', 'deep, rolling afro house', 'afro house with marimba and hand drums', 'spiritual afro house'],
 'tropical': ['tropical house for beach days', 'sunny tropical grooves with steel drums', 'island-breeze tropical house', 'beachside tropical house'],
 'futurebass': ['bright, bouncy future bass', 'big-chord future bass', 'euphoric future bass', 'colourful half-time future bass'],
 'nudisco': ['nu-disco grooves with live bass and guitar', 'sleek nu-disco', 'roller-rink nu-disco', 'funky nu-disco and boogie'],
 'progressive': ['emotional progressive house with big breakdowns', 'rolling progressive house', 'hypnotic progressive grooves', 'widescreen progressive house'],
 'tech': ['rolling tech house for the late hours', 'groovy, minimal tech house', 'percussive tech house', 'warehouse tech house'],
 'trance': ['uplifting sunset trance', 'euphoric melodic trance', 'balearic trance', 'soaring string trance'],
 'vocal': ['vocal-house energy, played on instruments', 'big-room vocal house instrumentals', 'diva-house instrumentals', 'gospel-tinged house instrumentals'],
 'soulful': ['soulful house keys and Sunday grooves', 'soulful house with organ and sax', 'jazzy soulful house', 'warm soulful grooves'],
 'disco': ['classic disco strings, brass and four-on-the-floor', 'mirrorball disco', 'string-swept disco', 'funky disco and boogie'],
 'french': ['filtered French touch house', 'French touch disco loops and filters', 'Parisian filter house', 'sun-bleached French touch'],
 'indiedance': ['indie dance with driving bass and guitars', 'synth-and-guitar indie dance', 'dark-disco indie dance', 'post-punk indie dance grooves'],
}


def plain(s): return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()


def build(old):
    rng = random.Random(1101)
    regions = list(H)
    taken = {plain(v['name']) for v in old.values()}
    stage_used = {}

    def name_ok(n):
        k = plain(n)
        if len(n) > 20 or k in taken: return False
        taken.add(k); return True

    def first(region, g):
        f, m, _ = H[region]; return rng.choice((f if g == 'female' else m).split())

    def stage_word():
        w = rng.choice(STAGE)
        while stage_used.get(w, 0) >= 7: w = rng.choice(STAGE)       # spread the stage surnames
        stage_used[w] = stage_used.get(w, 0) + 1; return w

    def solo(region, g, dj):
        f, m, sur = H[region]
        for _ in range(200):
            fn = first(region, g)
            r = rng.random()
            if dj: n = f'DJ {fn} {stage_word()}' if r < .55 else f'DJ {fn} {rng.choice(sur.split())}'
            else: n = f'{fn} {stage_word()}' if r < .7 else f'{fn} {rng.choice(sur.split())}'
            if name_ok(n): return n
        raise SystemExit('ran out of names for ' + region)

    def duo(r1, r2, g):
        gs = {'female': ('female', 'female'), 'male': ('male', 'male'), 'mixed': ('female', 'male')}[g]
        for _ in range(200):
            if rng.random() < .55: n = f'{first(r1, gs[0])} & {first(r2, gs[1])}'
            else: n = f'{first(r1, gs[0])} & {stage_word()}' if rng.random() < .3 else f'{stage_word()} {rng.choice(["Twins", "Duo", "Pair", "Two"])}'
            if name_ok(n): return n
        raise SystemExit('ran out of duo names')

    def collective():
        for _ in range(500):
            n = f'{rng.choice(ADJ)} {rng.choice(NOUN)} {rng.choice(COLLECTIVE)}' if rng.random() < .6 else f'{rng.choice(ADJ)} {rng.choice(NOUN)}'
            if name_ok(n): return n
        raise SystemExit('ran out of collective names')

    new_total = TOTAL - len(old); per = [new_total // len(STYLES) + (i < new_total % len(STYLES)) for i in range(len(STYLES))]
    roster, reg_cycle = {}, []
    for si, style in enumerate(STYLES):
        o = dict(old[style]); o.update(gender=o.get('gender', 'unspecified'), heritage=o.get('heritage', 'unspecified'), original=True)
        acts = [o]
        n = per[si]
        # per style: 46% solo producers/players, 24% DJs, 16% duos, 14% collectives/bands; solos & DJs split female/male
        kinds = (['producer'] * round(n * .46) + ['DJ'] * round(n * .24) + ['duo'] * round(n * .16))
        kinds += ['collective'] * (n - len(kinds)); rng.shuffle(kinds)
        gcount = {'female': 0, 'male': 0}
        for k in kinds:
            if not reg_cycle: reg_cycle = regions[:]; rng.shuffle(reg_cycle)
            region = reg_cycle.pop()
            if k in ('producer', 'DJ'):
                g = 'female' if gcount['female'] <= gcount['male'] else 'male'; gcount[g] += 1
                kind = k if k == 'DJ' else rng.choice(['producer', 'producer', 'producer', 'keyboardist', 'guitarist', 'multi-instrumentalist'])
                acts.append({'name': solo(region, g, k == 'DJ'), 'kind': kind, 'gender': g, 'heritage': region})
            elif k == 'duo':
                g = rng.choice(['female', 'male', 'mixed', 'mixed'])
                r2 = region if rng.random() < .6 else rng.choice(regions)
                acts.append({'name': duo(region, r2, g), 'kind': 'duo', 'gender': g,
                             'heritage': region if r2 == region else f'{region} + {r2}'})
            else:
                acts.append({'name': collective(), 'kind': rng.choice(['collective', 'band project', 'live band', 'producer collective']),
                             'gender': 'mixed', 'heritage': 'multi-heritage'})
            acts[-1]['line'] = rng.choice(LINES[style])
        roster[style] = acts
    return roster


if __name__ == '__main__':
    cur = json.load(open(OUT))
    old = {s: {k: v for k, v in a[0].items() if k not in ('original',)} for s, a in cur['roster'].items()} if 'roster' in cur else cur['artists']
    roster = build(old)
    n = sum(len(v) for v in roster.values())
    doc = {'note': ('Mirage Tropical Records roster (Sello, 1 Nov 2026: up to 1000 DJs and artists, male/female and many heritages). '
                    'All acts are fictional. Releases rotate through each style\'s roster: song_release.py next picks the act in the '
                    'style with the fewest releases (roster order breaks ties). "heritage" is the cultural origin of the names used. '
                    'The 15 original acts (original: true) come first. Rebuild with mirage/roster/build_roster.py.'),
           'count': n, 'roster': roster}
    with open(OUT, 'w') as f:
        f.write('{\n "note": ' + json.dumps(doc['note'], ensure_ascii=False) + ',\n "count": ' + str(n) + ',\n "roster": {\n')
        f.write(',\n'.join('  ' + json.dumps(s) + ': [\n' + ',\n'.join('   ' + json.dumps(a, ensure_ascii=False) for a in acts) + '\n  ]'
                           for s, acts in roster.items()))
        f.write('\n }\n}\n')
    print('wrote', n, 'acts')
