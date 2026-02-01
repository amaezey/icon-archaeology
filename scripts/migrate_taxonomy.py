#!/usr/bin/env python3
"""
Migrate to new taxonomy structure:
- 5 core categories (structural types)
- Themes (subject matter) - multiple allowed
- Vibes (aesthetic feeling) - multiple allowed

RULE: NEVER remove tags, only add/restructure.
"""

import json
from pathlib import Path
from collections import Counter

TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")
OUTPUT_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags-migrated.json")

# Map old categories to new 5 core categories
CATEGORY_MAP = {
    'object': 'object',
    'food': 'object',      # food items are objects
    'hardware': 'object',  # hardware items are objects
    'vehicle': 'object',   # vehicles are objects
    'nature': 'object',    # plants/landscapes are objects (or scenes)
    'character': 'character',
    'animal': 'character', # animals are characters
    'symbol': 'symbol',
    'ui': 'ui',
    'folder': 'ui',        # folders are UI elements
    'text': 'text',
    'office': 'object',    # office items are objects
    'sports': 'object',    # sports items are objects
}

# Old categories that become themes
CATEGORY_TO_THEME = {
    'food': 'food',
    'hardware': 'hardware',
    'vehicle': 'vehicle',
    'nature': 'nature',
    'animal': 'animal',
    'folder': 'folder',
    'office': 'office',
    'sports': 'sports',
}

# Keywords to extract themes from descriptions
THEME_KEYWORDS = {
    'food': ['food', 'fruit', 'vegetable', 'meat', 'bread', 'cake', 'pie', 'pizza', 'burger', 'sandwich', 'sushi', 'rice', 'noodle', 'soup', 'salad', 'cheese', 'egg', 'fish', 'chicken', 'beef', 'pork', 'dessert', 'candy', 'chocolate', 'ice cream', 'cookie', 'donut'],
    'drink': ['drink', 'coffee', 'tea', 'beer', 'wine', 'juice', 'soda', 'water', 'bottle', 'cup', 'mug', 'glass'],
    'japanese': ['japanese', 'japan', 'sushi', 'ramen', 'samurai', 'ninja', 'origami', 'bonsai', 'kimono', 'torii', 'manga', 'anime', 'kanji'],
    'christmas': ['christmas', 'santa', 'reindeer', 'snowman', 'candy cane', 'ornament', 'wreath', 'sleigh', 'present', 'gift'],
    'halloween': ['halloween', 'pumpkin', 'witch', 'ghost', 'skeleton', 'vampire', 'zombie', 'bat', 'spider', 'jack-o-lantern'],
    'scifi': ['robot', 'alien', 'spaceship', 'space', 'rocket', 'laser', 'ufo', 'android', 'cyborg', 'futuristic', 'satellite'],
    'fantasy': ['dragon', 'wizard', 'magic', 'fairy', 'unicorn', 'castle', 'sword', 'knight', 'elf', 'dwarf', 'wand'],
    'music': ['music', 'guitar', 'piano', 'drum', 'violin', 'microphone', 'headphone', 'speaker', 'note', 'instrument', 'trumpet', 'saxophone'],
    'sports': ['ball', 'basketball', 'football', 'soccer', 'tennis', 'golf', 'baseball', 'hockey', 'trophy', 'medal', 'bat', 'racket'],
    'office': ['folder', 'document', 'paper', 'clipboard', 'stapler', 'pencil', 'pen', 'desk', 'briefcase', 'calculator', 'notebook'],
    'kitchen': ['pan', 'pot', 'spoon', 'fork', 'knife', 'bowl', 'plate', 'cup', 'mug', 'cooking', 'chef', 'oven', 'stove', 'refrigerator'],
    'gaming': ['game', 'controller', 'joystick', 'arcade', 'pixel', 'mario', 'nintendo', 'playstation', 'xbox', 'console'],
    'military': ['tank', 'soldier', 'army', 'gun', 'rifle', 'helmet', 'camouflage', 'medal', 'grenade', 'missile', 'bomb'],
    'science': ['microscope', 'telescope', 'atom', 'molecule', 'flask', 'beaker', 'lab', 'scientist', 'dna', 'chemical'],
    'fashion': ['dress', 'shirt', 'pants', 'hat', 'shoe', 'boot', 'glasses', 'jewelry', 'watch', 'purse', 'handbag', 'tie'],
    'art': ['paint', 'brush', 'canvas', 'palette', 'sculpture', 'drawing', 'sketch', 'frame', 'easel'],
    'horror': ['blood', 'skull', 'monster', 'demon', 'scary', 'creepy', 'dark', 'evil', 'zombie', 'skeleton'],
    'animal': ['cat', 'dog', 'bird', 'fish', 'horse', 'cow', 'pig', 'chicken', 'duck', 'rabbit', 'mouse', 'bear', 'lion', 'tiger', 'elephant', 'monkey', 'frog', 'snake', 'turtle', 'penguin', 'owl', 'bee', 'butterfly'],
    'nature': ['tree', 'flower', 'plant', 'leaf', 'forest', 'mountain', 'ocean', 'beach', 'sun', 'moon', 'star', 'cloud', 'rain', 'snow', 'grass'],
    'vehicle': ['car', 'truck', 'bus', 'train', 'plane', 'airplane', 'helicopter', 'boat', 'ship', 'bicycle', 'motorcycle'],
    'hardware': ['computer', 'monitor', 'keyboard', 'mouse', 'printer', 'disk', 'drive', 'cpu', 'chip', 'cable', 'server'],
    'communication': ['phone', 'telephone', 'email', 'mail', 'letter', 'envelope', 'fax', 'radio'],
}

# Keywords to extract vibes from descriptions
VIBE_KEYWORDS = {
    'cute': ['cute', 'adorable', 'kawaii', 'sweet', 'lovely', 'tiny', 'little', 'baby'],
    'spooky': ['scary', 'creepy', 'dark', 'evil', 'sinister', 'skull', 'ghost', 'monster', 'horror', 'blood'],
    'playful': ['fun', 'happy', 'cheerful', 'silly', 'cartoon', 'colorful', 'smiling', 'grin'],
    'elegant': ['elegant', 'fancy', 'ornate', 'decorative', 'golden', 'royal', 'luxurious', 'beautiful'],
    'retro': ['vintage', 'classic', 'old', 'antique', 'retro', 'nostalgic'],
    'minimal': ['simple', 'clean', 'basic', 'plain', 'minimal', 'flat'],
    'cozy': ['warm', 'cozy', 'home', 'comfort', 'soft', 'fuzzy'],
    'quirky': ['weird', 'strange', 'unusual', 'odd', 'quirky', 'funny'],
    'technical': ['computer', 'electronic', 'digital', 'technical', 'mechanical', 'metal', 'gray'],
}

def extract_from_description(description, keywords_dict, existing_values):
    """Extract values from description, ADD to existing (never remove)."""
    values = set(existing_values) if existing_values else set()

    if not description:
        return list(values)

    desc_lower = description.lower()

    for value, keywords in keywords_dict.items():
        for keyword in keywords:
            if keyword in desc_lower:
                values.add(value)
                break

    # Remove empty strings
    values.discard('')

    return list(values)

def main():
    print("Migrating to new taxonomy")
    print("=" * 50)
    print("Categories: object, character, symbol, ui, text")
    print("Themes: multiple, extracted from old categories + descriptions")
    print("Vibes: multiple, extracted from descriptions")
    print("=" * 50)

    # Load tags
    with open(TAGS_FILE) as f:
        data = json.load(f)

    icons = data['icons']
    print(f"\nProcessing {len(icons)} icons")

    for icon in icons:
        # Get old category
        old_category = icon.get('primary', 'object')

        # Map to new category
        new_category = CATEGORY_MAP.get(old_category, 'object')
        icon['category'] = new_category

        # Start themes with existing secondary tags
        themes = set(icon.get('secondary', []))

        # Add old category as theme if applicable
        if old_category in CATEGORY_TO_THEME:
            themes.add(CATEGORY_TO_THEME[old_category])

        # Extract more themes from description
        description = icon.get('description', '')
        for theme, keywords in THEME_KEYWORDS.items():
            for keyword in keywords:
                if keyword in description.lower():
                    themes.add(theme)
                    break

        # Clean and save themes
        themes.discard('')
        icon['themes'] = sorted(list(themes))

        # Handle vibes - start with existing
        existing_vibe = icon.get('vibe', '')
        vibes = set([existing_vibe]) if existing_vibe else set()

        # Extract more vibes from description
        for vibe, keywords in VIBE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in description.lower():
                    vibes.add(vibe)
                    break

        # Clean and save vibes
        vibes.discard('')
        if not vibes:
            vibes.add('technical')  # default
        icon['vibes'] = sorted(list(vibes))

        # Keep old fields for backwards compat
        icon['primary'] = new_category  # update to new category
        icon['vibe'] = icon['vibes'][0]  # primary vibe
        icon['secondary'] = icon['themes']  # themes = secondary

    # Report
    print("\n" + "=" * 50)
    print("NEW DISTRIBUTION:")

    categories = Counter(i['category'] for i in icons)
    print("\nCategories (5 core):")
    for cat, count in categories.most_common():
        print(f"  {cat}: {count}")

    vibes = Counter()
    multi_vibe = 0
    for i in icons:
        if len(i['vibes']) > 1:
            multi_vibe += 1
        for v in i['vibes']:
            vibes[v] += 1
    print(f"\nVibes ({multi_vibe} icons have multiple):")
    for vibe, count in vibes.most_common():
        print(f"  {vibe}: {count}")

    themes = Counter()
    for i in icons:
        for t in i['themes']:
            themes[t] += 1
    print(f"\nThemes (top 20):")
    for theme, count in themes.most_common(20):
        print(f"  {theme}: {count}")

    # Save
    output_data = {'icons': icons}
    if 'deduplication' in data:
        output_data['deduplication'] = data['deduplication']
    output_data['taxonomy'] = {
        'version': 2,
        'categories': ['object', 'character', 'symbol', 'ui', 'text'],
        'description': 'Categories are structural types. Themes are subject matter. Vibes are aesthetic feeling.'
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")
    print("To apply: cp public/tags-migrated.json public/tags.json")

if __name__ == "__main__":
    main()
