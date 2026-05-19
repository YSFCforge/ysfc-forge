"""
YSFC Forge — Performance Categories

Officiell category-tree för performances.
Källa: Härlett ur Yamahas publicerade MODX M Data List
(© Yamaha Corporation). Endast funktionella fakta extraheras, för interoperabilitet med det odokumenterade
Y2L/Y2U-filformatet. Yamahas dokument återdistribueras inte här —
originalet finns hos Yamaha: https://download.yamaha.com
(sök "MODX M Data List").
16 main categories, varje med 8-10 sub categories.
Detta är category-strukturen som visas i Yamamas Browser.
"""

# {main_category: [sub_category, sub_category, ...]}
PERFORMANCE_CATEGORIES = {
    'Piano': ['Acoustic', 'Layer', 'Modern', 'Vintage', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Keyboard': ['Electric Piano', 'FM Piano', 'Clavi', 'Synth', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Organ': ['Tone Wheel', 'Combo', 'Pipe', 'Synth', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Guitar': ['Acoustic', 'Electric Clean', 'Distortion', 'Synth', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Bass': ['Acoustic', 'Electric', 'Synth', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Strings': ['Solo', 'Ensemble', 'Pizzicato', 'Synth', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Brass': ['Solo', 'Ensemble', 'Orchestra', 'Synth', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Woodwind': ['Saxophone', 'Flute', 'Woodwind', 'Reed / Pipe', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Syn Lead': ['Analog', 'Digital', 'Hip Hop', 'Dance', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Pad/Choir': ['Analog', 'Warm', 'Bright', 'Choir', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Syn Comp': ['Analog', 'Digital', 'Decay', 'Hook', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Chromatic Perc': ['Mallet', 'Bell', 'Synth Bell', 'Pitched Drum', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Drum / Perc': ['Drums', 'Percussion', 'Synth', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Sound FX': ['Moving', 'Ambient', 'Nature', 'Sci-Fi', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Musical FX': ['Moving', 'Ambient', 'Sweep', 'Hit', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
    'Ethnic': ['Bowed', 'Plucked', 'Struck', 'Blown', 'Rock/Pop', 'R&B/Hip Hop', 'Electronic', 'Jazz/World', 'No Assign'],
}


def get_main_categories():
    """Returns list of main categories in display order."""
    return list(PERFORMANCE_CATEGORIES.keys())


def get_sub_categories(main_cat):
    """Returns list of sub categories for a main category."""
    return PERFORMANCE_CATEGORIES.get(main_cat, [])


# Numerisk index-mapping (för byte-encoding)
# Main category index = position i listan
MAIN_CATEGORY_INDEX = {cat: i for i, cat in enumerate(PERFORMANCE_CATEGORIES.keys())}
INDEX_TO_MAIN_CATEGORY = {i: cat for cat, i in MAIN_CATEGORY_INDEX.items()}


if __name__ == '__main__':
    print(f"Main categories: {len(PERFORMANCE_CATEGORIES)}")
    for main, subs in PERFORMANCE_CATEGORIES.items():
        print(f"  {main}: {len(subs)} subs")
