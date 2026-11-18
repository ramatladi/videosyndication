# Nov 9 2026, part C: the 4 slots Sello unblocked on 10 Nov (19:00 SAST): "Do both 1 and 2".
# 16:00 = option 1 (same product, a different size than Nov 8); 20:00 = option 2 (a face product, body or sun angle).
# Facts from each dermalogica.co.za listing (read 10 Nov 2026). Image index 0 is the variant's packshot.
I = []
def item(sku, ch, slot, fmt, title, lead, facts, scenes, tags, hashtags, thumb, slug_suffix=''):
    I.append(dict(sku=sku, ch=ch, slot=slot, format=fmt, title=title, lead=lead, facts=facts, scenes=scenes, tags=tags,
                  hashtags=hashtags, thumb=thumb, slug_suffix=slug_suffix))

# ---------- Westville 16:00: option 1, the 295 mL size (Nov 8 featured the 177 mL) ----------
item('811478INT', 'skincare.durban', '16:00', 'short',
     'Dermalogica Clarifying Body Spray, 295 mL: After the Shower or the Gym #shorts',
     'Dermalogica clarifying body spray in the larger 295 mL size, in under a minute: when to use it and how, from the Westville body care desk.',
     ['Blemish-fighting body spray that helps clear clogged pores and minimize future body breakouts',
      'Salicylic acid (1.0%) exfoliates; witch hazel, tea tree oil and Moroccan argan oil help balance oil and reduce redness',
      'Ideal after the shower, post-workout or on the go; the mist disperses even upside down',
      'Spray onto clean, dry skin from about a foot and a half away; let it sink in 30-60 seconds; AM and/or PM'],
     [dict(type='cover', sub='295 mL size', say='Westville body care: the bigger bottle. Dermalogica clarifying body spray, two hundred ninety-five milliliters.'),
      dict(type='photo', image=4, kicker='WHEN', headline='After the shower or the gym', say='The listing names three moments for it: after the shower, after a workout, or on the go.'),
      dict(type='figure', image=7, kicker='THE FORMAT', headline='Sprays even upside down', say='The mist even disperses upside down, so hard-to-reach spots like the back are covered.'),
      dict(type='figure', image=1, kicker='INSIDE', headline='Salicylic acid + botanicals', say='Salicylic acid exfoliates, while witch hazel, tea tree oil and argan oil help balance oil and reduce redness.'),
      dict(type='steps', kicker='HOW TO USE', headline='Morning, night, or both', items=['Cleanse first', 'Clean, dry skin', '30-60 seconds to dry'],
           say='Cleanse first, spray onto clean, dry skin, and give it thirty to sixty seconds before getting dressed.'),
      dict(type='end', sub='295 mL', say='Clarifying body spray, the two hundred ninety-five milliliter size. The link is in the description.')],
     ['dermalogica clarifying body spray', 'clarifying body spray 295ml', 'body breakout spray', 'salicylic acid body spray', 'post workout skincare', 'westville', 'durban skincare'],
     '#Dermalogica #ClarifyingBodySpray #BodyCare #shorts', dict(text='After the gym', kicker='WESTVILLE', layout='photo', photo=4), slug_suffix='-295ml')

# ---------- Westville 20:00: option 2, a face product with a body angle (the neck) ----------
item('111369', 'skincare.durban', '20:00', 'short',
     'Dermalogica Phyto Nature Firming Serum: Don\'t Skip the Neck #shorts',
     'Dermalogica phyto nature firming serum, 40 mL, in under a minute: a dual-phase serum the listing says to smooth over the face and neck, from the Westville body care desk.',
     ['Dual-phase serum: highly active botanicals with biomimetic technology to reduce visible signs of skin aging',
      'Flash-firms, lifts and revitalizes, per the listing',
      'Dispense 1-2 pumps, blend the two serums in the palm, smooth over cleansed face and neck; morning and/or evening; follow with moisturizer'],
     [dict(type='cover', sub='40 mL', say='Westville body care usually starts below the neck. Tonight, a serum that goes right there: Dermalogica phyto nature firming serum.'),
      dict(type='figure', image=1, kicker='WHAT IT DOES', headline='Flash-firms, lifts, revitalizes', say='The listing calls it a dual-phase serum that flash-firms, lifts and revitalizes, to reduce visible signs of aging.'),
      dict(type='photo', image=5, kicker='TWO PHASES', headline='Blend in your palm', say='There are two serums in one bottle. Dispense one to two pumps and blend them in your palm.'),
      dict(type='figure', image=2, kicker='INSIDE', headline='Botanicals at work', say='Inside are botanicals, including camu camu, Moroccan rockrose and Madagascar green coffee bean.'),
      dict(type='steps', kicker='HOW TO USE', headline='Face and neck', items=['1-2 pumps, blended', 'Over face and neck', 'Moisturizer on top'],
           say='Smooth it over a cleansed face and neck, morning or evening, then follow with your moisturizer.'),
      dict(type='end', sub='40 mL', say='Phyto nature firming serum, forty milliliters. The link is in the description.')],
     ['dermalogica phyto nature firming serum', 'phyto nature firming serum', 'neck serum', 'firming serum', 'face and neck skincare', 'westville', 'durban skincare'],
     '#Dermalogica #PhytoNature #FirmingSerum #shorts', dict(text="Don't skip the neck", kicker='WESTVILLE', layout='photo', photo=5))

# ---------- Cape Town 16:00: option 1, the 50 mL size (Nov 8 featured the 15 mL) ----------
item('111006', 'dermatology.capetown', '16:00', 'short',
     'Dermalogica Dynamic Skin Recovery SPF50, 50 mL: Polypeptides + White Tea #shorts',
     'Dermalogica dynamic skin recovery spf50 in the 50 mL size, in under a minute: what\'s inside and where it sits in a routine, from the Cape Town daily sun care desk.',
     ['3-in-1 daily moisturizer that visibly firms, hydrates and protects with Broad Spectrum SPF50',
      'Polypeptide blend helps improve the appearance of photoaged skin; White Tea gives antioxidant protection against free radicals',
      'Non-greasy formula blends into skin for a flawless finish',
      'After cleansing and toning, apply a generous amount to face and neck, preferably 30 minutes before sun exposure'],
     [dict(type='cover', sub='50 mL size', say='Cape Town daily sun care: the full-size bottle of Dermalogica dynamic skin recovery SPF fifty, fifty milliliters.'),
      dict(type='figure', image=3, kicker='INSIDE', headline='Polypeptides + white tea', say='A polypeptide blend helps improve the look of photoaged skin, and white tea gives antioxidant protection against free radicals.'),
      dict(type='figure', image=1, kicker='THE FEEL', headline='Non-greasy, sheer finish', say='The formula is non-greasy and blends into the skin for a flawless finish.'),
      dict(type='figure', image=2, kicker='IN A ROUTINE', headline='The final morning step', say='It goes on after cleansing and toning, a generous amount over the face and neck.'),
      dict(type='note', kicker='TIMING', headline='About 30 minutes before the sun', say='The listing says to apply it, preferably, thirty minutes before sun exposure.'),
      dict(type='end', sub='50 mL', say='Dynamic skin recovery SPF fifty, the fifty milliliter size. The link is in the description.')],
     ['dermalogica dynamic skin recovery spf50', 'dynamic skin recovery spf50 50ml', 'spf50 moisturizer', 'daily sunscreen', 'cape town', 'cape town skincare'],
     '#Dermalogica #DynamicSkinRecovery #SPF50 #shorts', dict(text='SPF50 + white tea', kicker='CAPE TOWN', layout='right'), slug_suffix='-50ml')

# ---------- Cape Town 20:00: option 2, a face product with a sun angle (the night after) ----------
item('111504', 'dermatology.capetown', '20:00', 'short',
     'Dermalogica BioLumin-C Night Restore Serum: Sun Care Ends at Sunset? #shorts',
     'Dermalogica biolumin-c night restore serum, 25 mL, in under a minute: the night step the listing says helps reverse daytime damage, from the Cape Town daily sun care desk.',
     ['Night serum that helps restore radiance, hydration and tone overnight',
      'Ultra-stable vitamin C and a pro-vitamin D complex help repair the moisture barrier during sleep; helps reverse daytime damage',
      'After cleansing and toning, apply 3-4 drops over face and neck before bed; keep out of eyes',
      'Daytime: broad spectrum SPF'],
     [dict(type='cover', sub='25 mL', say='Cape Town daily sun care, after dark: Dermalogica biolumin-c night restore serum.'),
      dict(type='figure', image=6, kicker='AFTER THE DAY', headline='Helps reverse daytime damage', say='SPF is the daytime job. At night, the listing says, skin enters a regenerative phase, and this serum helps reverse daytime damage.'),
      dict(type='figure', image=5, kicker='INSIDE', headline='Vitamin C + pro-vitamin D', say='Inside: ultra-stable vitamin C and a pro-vitamin D complex, to help repair the moisture barrier while you sleep.'),
      dict(type='figure', image=7, kicker='HOW TO USE', headline='3-4 drops before bed', say='After cleansing and toning, apply three to four drops over the face and neck before bed, keeping it out of the eyes.'),
      dict(type='figure', image=9, kicker='NEXT MORNING', headline='Back to SPF', say='Then in the morning, it\'s back to a broad spectrum SPF.'),
      dict(type='end', sub='25 mL', say='Biolumin-c night restore serum, twenty-five milliliters. The link is in the description.')],
     ['dermalogica biolumin-c night restore serum', 'biolumin-c night restore', 'vitamin c night serum', 'after sun skincare routine', 'cape town', 'cape town skincare'],
     '#Dermalogica #BioLuminC #NightSerum #shorts', dict(text='After a sunny day', kicker='CAPE TOWN', layout='photo', photo=2))
