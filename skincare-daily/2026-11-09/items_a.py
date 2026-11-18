# Nov 9 2026, part A: the six 08:00 Shorts. Facts from each dermalogica.co.za listing (read 9 Nov 2026).
I = []
def item(sku, ch, slot, fmt, title, lead, facts, scenes, tags, hashtags, thumb):
    I.append(dict(sku=sku, ch=ch, slot=slot, format=fmt, title=title, lead=lead, facts=facts, scenes=scenes, tags=tags, hashtags=hashtags, thumb=thumb))

item('111506INT', 'skincare.joburg', '08:00', 'short',
     'Dermalogica Breakout Biotic Moisturiser: A Lightweight Gel Texture #shorts',
     'Dermalogica breakout biotic moisturiser, 50 mL, in under a minute: a lightweight breakout-targeting gel, from the Rosebank texture desk.',
     ['Daily breakout-targeting gel moisturizer that helps prevent breakouts', 'Prebiotic blend (Indian mulberry, glutamic acid, agave) hydrates and supports the skin\'s microbiome; bioengineered plankton extract and glycerin', 'After cleansing and toning, apply over face and neck in light, upward strokes; follow with SPF in the morning'],
     [dict(type='cover', sub='50 mL gel moisturizer', say='Rosebank texture desk, in under a minute: Dermalogica breakout biotic moisturiser.'),
      dict(type='photo', image=3, kicker='THE TEXTURE', headline='A lightweight gel', say='The texture is a lightweight, daily gel, made to hydrate while it targets breakouts.'),
      dict(type='figure', image=0, kicker='ON THE LABEL', headline='Treats + prevents breakouts daily', say='The label promise: it treats and helps prevent breakouts daily, and a prebiotic blend hydrates and supports the skin\'s microbiome.'),
      dict(type='steps', image=1, kicker='HOW TO USE', headline='Morning and night', items=['After cleansing and toning', 'Face and neck, upward strokes', 'SPF on top in the morning'], say='After cleansing and toning, apply it over the face and neck in light, upward strokes, and follow with SPF in the morning.'),
      dict(type='end', sub='50 mL', say='Breakout biotic moisturiser, fifty milliliters. The link is in the description.')],
     ['dermalogica breakout biotic moisturiser', 'breakout biotic moisturiser', 'gel moisturizer', 'moisturizer for breakouts', 'rosebank', 'johannesburg skincare'],
     '#Dermalogica #BreakoutBiotic #GelMoisturizer #shorts', dict(text='A breakout gel moisturizer', kicker='ROSEBANK', layout='photo', photo=3))

item('W101717', 'skincare.durban', '08:00', 'short',
     'Dermalogica Clearing Skin Wash: A Foaming Wash for Face, Chest and Back #shorts',
     'Dermalogica clearing skin wash, 500 mL, in under a minute: a foaming wash the listing says can go beyond the face, from the Westville body care desk.',
     ['Foaming cleanser that clears away excess oil without stripping skin and helps prevent future breakouts', 'Encapsulated salicylic acid (0.5%); rice-derived phytic acid; menthol and camphor cool the skin', 'Pea-sized amount lathered in wet hands, massaged onto damp skin, rinse with warm water; the listing FAQ says it can also be used on the chest or back'],
     [dict(type='cover', sub='500 mL pump', say='Westville body care, in under a minute: Dermalogica clearing skin wash, and where else it can go.'),
      dict(type='figure', image=2, kicker='WHAT IT DOES', headline='Clears oil without stripping', say='It\'s a foaming wash that clears away excess oil without stripping the skin, with point five percent encapsulated salicylic acid.'),
      dict(type='photo', image=6, kicker='BEYOND THE FACE', headline='Chest and back, too', say='It\'s made as a facial cleanser, but the listing says it can also be used on areas like the chest or back.'),
      dict(type='photo', image=4, kicker='HOW TO USE', headline='Pea-sized, lather, rinse', say='Work a pea-sized amount into a lather in wet hands, massage it onto damp skin, then rinse thoroughly with warm water.'),
      dict(type='end', sub='500 mL', say='Clearing skin wash, five hundred milliliters. The link is in the description.')],
     ['dermalogica clearing skin wash', 'clearing skin wash', 'body acne wash', 'salicylic acid cleanser', 'westville', 'durban skincare'],
     '#Dermalogica #ClearingSkinWash #BodyCare #shorts', dict(text='Face, chest and back', kicker='WESTVILLE', layout='photo', photo=6))

item('111326', 'dermatologist.joburg', '08:00', 'short',
     'Dermalogica Intensive Moisture Cleanser: Cleanse Step for Dry Skin #shorts',
     'Dermalogica intensive moisture cleanser, 150 mL, in under a minute: the cleanse step for dry skin, from the Midrand routine desk.',
     ['Light, creamy cleanser with BioReplenish Complex that removes impurities while nourishing dry, depleted skin', 'Coconut oil and murumuru seed butter phytoactives help protect barrier lipids', 'Lather a pea-size amount in very wet hands, massage onto damp face and neck, rinse; twice daily'],
     [dict(type='cover', sub='150 mL', say='Midrand routine desk, step one for dry skin: Dermalogica intensive moisture cleanser.'),
      dict(type='figure', image=1, kicker='WHAT IT IS', headline='A creamy cleanser for dry skin', say='It\'s a light, creamy cleanser that removes impurities while nourishing dry, depleted skin, with a BioReplenish Complex.'),
      dict(type='photo', image=4, kicker='HOW TO USE', headline='Pea-sized, very wet hands', say='Lather a pea-size amount in very wet hands, massage it onto a damp face and neck, then rinse with warm water.'),
      dict(type='steps', image=5, kicker='IN YOUR ROUTINE', headline='Step one, twice a day', items=['Cleanse: this step', 'Tone', 'Treat', 'Moisturize'], say='Use it morning and night, as the cleanse step before toner and moisturizer. We\'re not dermatologists, just reading the listing.'),
      dict(type='end', sub='150 · 295 mL', say='Intensive moisture cleanser, in one hundred fifty and two hundred ninety-five milliliters. The link is in the description.')],
     ['dermalogica intensive moisture cleanser', 'intensive moisture cleanser', 'cleanser for dry skin', 'cream cleanser', 'skincare routine step one', 'midrand'],
     '#Dermalogica #IntensiveMoistureCleanser #SkincareRoutine #shorts', dict(text='Step one for dry skin', kicker='MIDRAND', layout='left'))

item('111447', 'dermatology.joburg', '08:00', 'short',
     'Dermalogica Post-Breakout Fix Label: Three Ingredients to Find #shorts',
     'Dermalogica post-breakout fix, 15 mL, label check in under a minute: the ingredients behind a post-breakout mark treatment.',
     ['Gel-cream spot treatment that helps fade and brighten post-breakout marks (red and dark spots)', 'Hexylresorcinol, salicylic acid, carob seed extract and squalane', 'After cleansing and toning, apply a small amount to the post-breakout spot, twice a day or as needed, until the mark fades'],
     [dict(type='cover', sub='Label check', say='Bedfordview label check: three ingredients to find on Dermalogica post-breakout fix.'),
      dict(type='figure', image=2, kicker='THE INGREDIENTS', headline='Hexylresorcinol, salicylic acid, squalane', say='Find these: hexylresorcinol to help fade marks and brighten, salicylic acid to gently exfoliate, and squalane to moisturize. Carob seed extract is in there too.'),
      dict(type='photo', image=4, kicker='WHAT IT\'S FOR', headline='The marks a breakout leaves', say='It\'s a gel-cream spot treatment for the red and dark marks a breakout leaves behind.'),
      dict(type='steps', image=6, kicker='DIRECTIONS', headline='On the spot, until it fades', items=['After cleansing and toning', 'A small amount on the mark', 'Twice a day, until it fades'], say='After cleansing and toning, apply a small amount right on the mark, twice a day or as needed, until it fades. We\'re not dermatologists or doctors.'),
      dict(type='end', sub='15 mL', say='Post-breakout fix, fifteen milliliters. The link is in the description.')],
     ['dermalogica post-breakout fix', 'post-breakout fix', 'post acne marks', 'spot treatment', 'how to read skincare labels', 'bedfordview'],
     '#Dermalogica #PostBreakoutFix #SkincareLabels #shorts', dict(text='3 ingredients to find', kicker='LABEL CHECK', layout='right'))

item('111430', 'dermatology.durban', '08:00', 'short',
     'Dermalogica Micro-Pore Mist 118ml: When to Spritz It in Your Routine #shorts',
     'Dermalogica micro-pore mist, 118 mL, in under a minute: when to spritz it, from the uMhlanga hydration desk.',
     ['A mist to minimize the look of pores, reduce excess oil and help diminish the appearance of post-breakout marks', 'Niacinamide; wild rose hips flavonoid complex; cucumber extract', 'Spritz on after cleansing morning and night, or throughout the day as needed'],
     [dict(type='cover', sub='118 mL', say='uMhlanga hydration desk: when to spritz Dermalogica micro-pore mist.'),
      dict(type='figure', image=3, kicker='INSIDE', headline='Niacinamide + wild rose hips', say='It\'s made with niacinamide and a wild rose hips flavonoid complex, to help minimize the look of pores and reduce oily shine.'),
      dict(type='photo', image=5, kicker='THE FEEL', headline='Cucumber for a cool refresh', say='Cucumber extract adds a cool, refreshing feel.'),
      dict(type='steps', image=6, kicker='WHEN TO SPRITZ', headline='After cleansing, or any time', items=['After cleansing, morning + night', 'Then serum and moisturizer', 'Again during the day, as needed'], say='Spritz it on after cleansing, morning and night, before the rest of your layers, or any time during the day.'),
      dict(type='end', sub='118 mL', say='Micro-pore mist, one hundred eighteen milliliters. The link is in the description.')],
     ['dermalogica micro-pore mist', 'micro-pore mist', 'pore minimizing mist', 'niacinamide mist', 'how to layer skincare', 'umhlanga'],
     '#Dermalogica #MicroPoreMist #Layering #shorts', dict(text='When to spritz', kicker='UMHLANGA', layout='photo', photo=1))

item('111013-01', 'dermatology.capetown', '08:00', 'short',
     'Dermalogica PowerBright Moisturiser SPF50: Daily SPF for Dark Spots #shorts',
     'Dermalogica powerbright moisturiser spf50, 50 mL, in under a minute: a daily SPF moisturizer, from the Cape Town daily sun care desk.',
     ['Daily SPF50 moisturizer that helps shield against dark spots', 'Niacinamide helps balance skin tone; brown algae helps combat oxidative stress from pollution; hyaluronic acid and safflower oil hydrate', 'Apply over face and neck, avoiding the eyes, preferably 30 minutes before sun; best after PowerBright Dark Spot Serum'],
     [dict(type='cover', sub='50 mL', say='Cape Town daily sun care, in under a minute: Dermalogica powerbright moisturiser SPF fifty.'),
      dict(type='figure', image=1, kicker='WHAT IT DOES', headline='Shields against dark spots', say='It\'s a daily moisturizer with SPF fifty that helps shield the skin against dark spots.'),
      dict(type='bullets', image=2, kicker='INSIDE', headline='Beyond the SPF', items=['Niacinamide: balances tone', 'Brown algae: pollution stress', 'Hyaluronic acid + safflower oil'], say='Inside, niacinamide helps balance skin tone, brown algae helps combat oxidative stress from pollution, and hyaluronic acid and safflower oil hydrate.'),
      dict(type='photo', image=3, kicker='HOW TO WEAR IT', headline='About 30 minutes before sun', say='Apply it over the face and neck, avoiding the eyes, preferably thirty minutes before sun exposure.'),
      dict(type='end', sub='50 mL', say='Powerbright moisturiser SPF fifty, fifty milliliters. The link is in the description.')],
     ['dermalogica powerbright moisturiser spf50', 'powerbright moisturiser spf50', 'spf50 moisturizer', 'daily sunscreen', 'dark spots sunscreen', 'cape town'],
     '#Dermalogica #PowerBright #DailySPF #shorts', dict(text='Daily SPF50', kicker='CAPE TOWN', layout='center'))
