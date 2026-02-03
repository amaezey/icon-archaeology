#!/usr/bin/env python3
"""
Enrich icon tags from collection names, display names, and paths.

This script adds themes based on metadata that the original migration missed.
RULE: NEVER remove tags, only ADD.

Sources used:
1. Collection names (e.g., "Hide's Sushi Icons" → food, japanese)
2. Display names (e.g., Japanese characters → japanese)
3. Path components (e.g., "25 Days Before Christmas" → christmas)
"""

import json
import re
from pathlib import Path
from collections import Counter

TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")
OUTPUT_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags-enriched.json")

# Collection name patterns → themes
# Format: substring in collection name → list of themes to add
COLLECTION_THEMES = {
    # Sports
    'series 2000': ['sports', 'football'],
    'euro 2000': ['sports', 'football'],
    'go for sydney': ['sports', 'olympics'],
    'manchester united': ['sports', 'football'],
    'perugia': ['sports', 'football'],
    'paraguay': ['sports', 'football'],
    'j league': ['sports', 'football'],
    'balls': ['sports'],

    # Food - General
    'snack': ['food'],
    'ice cream': ['food', 'dessert'],
    'coffee shop': ['food', 'drink', 'coffee'],
    'coffee icons': ['food', 'drink', 'coffee'],
    'tea icons': ['food', 'drink'],
    'tea time': ['food', 'drink'],
    'bento': ['food', 'japanese'],
    'sushi': ['food', 'japanese'],
    'cutlet': ['food', 'japanese'],
    'donut': ['food', 'dessert'],
    'bakery': ['food', 'dessert'],
    'breakfast': ['food'],
    'osechi': ['food', 'japanese'],
    'okashi': ['food', 'japanese', 'dessert'],
    'edibles': ['food'],
    'street food': ['food'],
    'anna millers': ['food', 'dessert'],
    'vegetable': ['food'],
    'delicatessen': ['food'],
    'haagen-dazs': ['food', 'dessert'],
    'korean food': ['food', 'korean'],
    'nostalgic bread': ['food'],
    'bread': ['food'],
    'hot manjuh': ['food', 'japanese'],
    'chinese sweets': ['food', 'dessert'],
    'vegetarian': ['food'],
    'full dinners': ['food'],
    'otsumami': ['food', 'japanese'],
    'cake': ['food', 'dessert'],
    'curry': ['food'],
    'pie and tarte': ['food', 'dessert'],
    'fujiya': ['food', 'japanese', 'dessert'],
    'chicken wings': ['food'],
    'pizza': ['food'],
    'candy hearts': ['food', 'dessert'],
    'tokyo souvenirs': ['food', 'japanese'],
    'western dishes': ['food'],
    'fast food': ['food'],
    'chinese food': ['food'],
    'asian': ['food'],
    'cafe menu': ['food', 'drink'],
    'groceries': ['food'],
    'kitchen': ['food', 'kitchen'],
    'afternoon tea': ['food', 'drink', 'dessert'],
    'sweets': ['food', 'dessert'],

    # Japanese
    'ultraman': ['japanese', 'anime', 'scifi'],
    'proximity-j': ['japanese'],
    'natsu-yasumi': ['japanese'],

    # Christmas
    'christmas': ['christmas', 'holiday'],
    'first snow': ['christmas', 'winter'],
    'snowy town': ['christmas', 'winter'],
    'charlie brown christmas': ['christmas', 'cartoon'],

    # Halloween
    'halloween': ['halloween', 'spooky'],
    'great pumpkin': ['halloween', 'cartoon'],

    # Space/SciFi
    'solar system': ['space', 'scifi'],
    'space': ['space', 'scifi'],
    'a long time ago': ['scifi', 'starwars'],
    'star wars': ['scifi', 'starwars'],
    'matrix': ['scifi'],
    'apollo': ['space', 'scifi'],
    'aeon flux': ['scifi', 'cartoon'],

    # UI/Mac
    'yosemite': ['ui', 'apple'],
    'liquid folder': ['ui'],
    'liquid button': ['ui'],
    'copland': ['ui', 'apple'],
    'os x': ['ui', 'apple'],
    'classic x': ['ui', 'apple'],
    'interfacial': ['ui'],
    'apple desktop': ['hardware', 'apple'],
    'apple portable': ['hardware', 'apple'],
    'imac': ['hardware', 'apple'],
    'ibook': ['hardware', 'apple'],
    'palm v': ['hardware'],
    'palm pilot': ['hardware'],
    'webcam': ['hardware'],
    'aibo': ['hardware', 'robot'],
    'photonica hardware': ['hardware'],
    'power pc': ['hardware', 'apple'],
    '680x0': ['hardware', 'apple', 'retro'],

    # Music
    'guitar': ['music'],
    'phlatt audio': ['music'],
    'music studio': ['music'],
    'the cds': ['music'],

    # Animals/Characters
    'tabby': ['animal', 'cat'],
    'peanuts': ['cartoon', 'cute'],
    'macquarium': ['animal', 'fish'],
    'sesami street': ['cartoon', 'cute'],
    'simpsons': ['cartoon'],
    'furbie': ['toy', 'cute'],
    'archie': ['cartoon'],
    'thunderbirds': ['scifi', 'retro'],

    # Retro
    'retroish': ['retro'],
    'newtcons': ['retro', 'apple'],
    'nostalgic toy': ['retro', 'toy'],
    'nostalgic ice cream': ['retro', 'food', 'japanese'],

    # Tools/Hardware
    'tools': ['tools'],
    'mountaineering': ['sports', 'outdoor'],
    'tools of design': ['tools', 'art'],
    'junk drawer': ['tools'],

    # Household
    'bathroom': ['household'],
    'cleaning': ['household'],
    'warehouse': ['household'],
    'boxes & containers': ['household'],

    # Heraldry/Symbols
    'coat of arms': ['heraldry', 'symbol'],
    'roundels': ['symbol'],

    # Nature
    'flowers': ['nature', 'plant'],
    'spring fling': ['nature', 'spring'],

    # Valentine
    'valentine': ['valentine', 'holiday'],

    # Gaming
    'diablo': ['gaming', 'fantasy'],

    # Cinema/Media
    'cinema tools': ['film'],
    'eworld': ['internet', 'retro'],

    # St Patrick
    'st. patty': ['holiday', 'irish'],
    'ireland': ['irish'],

    # Fantasy
    'knights': ['fantasy', 'medieval'],
    'ravenswood manor': ['fantasy', 'spooky'],

    # Native/Cultural
    'native american': ['cultural'],
    'western': ['western'],

    # Misc branded
    '3d-licious': ['3d'],
    'sketchcons': ['sketch', 'art'],
    'graffiti': ['art', 'urban'],
    'clones': ['scifi'],
    'alive': ['ui'],
    'silencio': ['minimal'],
    'open me': ['ui'],
    'box me': ['ui'],
    'epack': ['ui'],
    'bazuin': ['ui'],
    'geometria': ['geometric', 'technical'],
    'flat-ericons': ['minimal', 'ui'],
    're-definition': ['ui'],
}

# Collection name patterns → vibes
COLLECTION_VIBES = {
    'cute': ['cute'],
    'cartoon': ['playful'],
    'nostalgic': ['retro'],
    'retro': ['retro'],
    'liquid': ['elegant'],
    'sketch': ['quirky'],
    'graffiti': ['quirky'],
    '3d': ['technical'],
    'geometria': ['minimal', 'technical'],
    'flat': ['minimal'],
    'halloween': ['spooky'],
    'ravenswood': ['spooky'],
    'silencio': ['minimal'],
    'fanciful': ['playful'],
}

# Display name patterns → themes
DISPLAY_NAME_THEMES = {
    # Japanese text detection (hiragana, katakana, kanji ranges)
    'japanese_chars': ['japanese'],

    # Sports player names often have numbers
    # We'll handle this specially
}

def has_japanese(text):
    """Check if text contains Japanese characters."""
    if not text:
        return False
    for char in text:
        code = ord(char)
        # Hiragana: 3040-309F, Katakana: 30A0-30FF, CJK: 4E00-9FFF
        if (0x3040 <= code <= 0x309F or
            0x30A0 <= code <= 0x30FF or
            0x4E00 <= code <= 0x9FFF):
            return True
    return False

def extract_themes_from_collection(collection, path):
    """Extract themes from collection name and path."""
    themes = set()

    # Check collection name
    if collection:
        collection_lower = collection.lower()
        for pattern, theme_list in COLLECTION_THEMES.items():
            if pattern in collection_lower:
                themes.update(theme_list)

    # Check path components
    if path:
        for component in path:
            component_lower = component.lower()
            for pattern, theme_list in COLLECTION_THEMES.items():
                if pattern in component_lower:
                    themes.update(theme_list)

    return themes

def extract_vibes_from_collection(collection):
    """Extract vibes from collection name."""
    vibes = set()

    if collection:
        collection_lower = collection.lower()
        for pattern, vibe_list in COLLECTION_VIBES.items():
            if pattern in collection_lower:
                vibes.update(vibe_list)

    return vibes

def extract_themes_from_display_name(display_name):
    """Extract themes from display name."""
    themes = set()

    if display_name:
        # Japanese character detection
        if has_japanese(display_name):
            themes.add('japanese')

    return themes

def main():
    print("=" * 60)
    print("Enriching tags from collection names, paths, display names")
    print("=" * 60)
    print("\nRULE: Only ADDING tags, never removing.\n")

    # Load current tags
    with open(TAGS_FILE) as f:
        data = json.load(f)

    icons = data['icons']
    print(f"Processing {len(icons)} icons\n")

    # Track what we add
    themes_added = Counter()
    vibes_added = Counter()
    icons_enriched = 0

    for icon in icons:
        collection = icon.get('collection', '')
        path = icon.get('path', [])
        display_name = icon.get('display_name', '')

        # Get existing themes and vibes
        existing_themes = set(icon.get('themes', []))
        existing_vibes = set(icon.get('vibes', []))

        # Extract new themes
        new_themes = set()
        new_themes.update(extract_themes_from_collection(collection, path))
        new_themes.update(extract_themes_from_display_name(display_name))

        # Extract new vibes
        new_vibes = extract_vibes_from_collection(collection)

        # Only add what's actually new
        themes_to_add = new_themes - existing_themes
        vibes_to_add = new_vibes - existing_vibes

        if themes_to_add or vibes_to_add:
            icons_enriched += 1

            # Update themes
            if themes_to_add:
                icon['themes'] = sorted(list(existing_themes | themes_to_add))
                icon['secondary'] = icon['themes']  # backwards compat
                for t in themes_to_add:
                    themes_added[t] += 1

            # Update vibes
            if vibes_to_add:
                icon['vibes'] = sorted(list(existing_vibes | vibes_to_add))
                icon['vibe'] = icon['vibes'][0]  # backwards compat
                for v in vibes_to_add:
                    vibes_added[v] += 1

    # Report
    print(f"Icons enriched: {icons_enriched} / {len(icons)}")

    print(f"\nThemes added ({sum(themes_added.values())} total):")
    for theme, count in themes_added.most_common(30):
        print(f"  {theme}: +{count}")

    print(f"\nVibes added ({sum(vibes_added.values())} total):")
    for vibe, count in vibes_added.most_common():
        print(f"  {vibe}: +{count}")

    # Final distribution
    print("\n" + "=" * 60)
    print("FINAL DISTRIBUTION:")

    all_themes = Counter()
    for icon in icons:
        for t in icon.get('themes', []):
            all_themes[t] += 1

    print(f"\nAll themes (top 40):")
    for theme, count in all_themes.most_common(40):
        print(f"  {theme}: {count}")

    all_vibes = Counter()
    for icon in icons:
        for v in icon.get('vibes', []):
            all_vibes[v] += 1

    print(f"\nAll vibes:")
    for vibe, count in all_vibes.most_common():
        print(f"  {vibe}: {count}")

    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")
    print("To apply: cp public/tags-enriched.json public/tags.json")

if __name__ == "__main__":
    main()
