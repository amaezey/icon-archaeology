#!/usr/bin/env python3
"""
Reassess and consolidate taxonomy based on descriptions.
- Consolidate categories (merge rare ones)
- Consolidate vibes to core set
- Extract themes from descriptions
- Clean up empty/duplicate values
"""

import json
import re
from pathlib import Path
from collections import Counter

TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")
OUTPUT_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags-retagged.json")

# Consolidated taxonomy
CATEGORY_MAP = {
    # Keep these as-is
    'object': 'object',
    'food': 'food',
    'character': 'character',
    'hardware': 'hardware',
    'ui': 'ui',
    'symbol': 'symbol',
    'folder': 'folder',
    'nature': 'nature',
    'animal': 'animal',
    'vehicle': 'vehicle',
    'text': 'text',
    # Merge rare ones
    'office': 'object',
    'sports': 'object',
}

# Core vibes (consolidate the 40+ down to ~10)
VIBE_MAP = {
    # Keep core vibes
    'technical': 'technical',
    'playful': 'playful',
    'cozy': 'cozy',
    'minimal': 'minimal',
    'retro': 'retro',
    'elegant': 'elegant',
    'quirky': 'quirky',
    'spooky': 'spooky',
    'cute': 'cute',
    # Map others to closest core vibe
    'mystical': 'spooky',
    'fantasy': 'playful',
    'festive': 'playful',
    'mysterious': 'spooky',
    'ancient': 'retro',
    'traditional': 'retro',
    'practical': 'technical',
    'rustic': 'cozy',
    'heroic': 'playful',
    'whimsical': 'quirky',
    'medieval': 'retro',
    'refreshing': 'playful',
    'patriotic': 'playful',
    'wise': 'elegant',
    'dramatic': 'elegant',
    'cheerful': 'playful',
    'fierce': 'spooky',
    'formal': 'elegant',
    'artistic': 'elegant',
    'professional': 'technical',
    'adventurous': 'playful',
    'scholarly': 'elegant',
    'military': 'technical',
    'authoritative': 'technical',
    'cool': 'playful',
    'majestic': 'elegant',
    'clean': 'minimal',
    'fresh': 'minimal',
    'decorative': 'elegant',
    'celebratory': 'playful',
    'creative': 'quirky',
    'powerful': 'technical',
}

# Keywords to extract themes from descriptions
THEME_KEYWORDS = {
    'japanese': ['japanese', 'japan', 'sushi', 'ramen', 'samurai', 'ninja', 'origami', 'bonsai', 'kimono', 'torii', 'manga', 'anime'],
    'christmas': ['christmas', 'santa', 'reindeer', 'snowman', 'candy cane', 'ornament', 'wreath', 'sleigh'],
    'halloween': ['halloween', 'pumpkin', 'witch', 'ghost', 'skeleton', 'vampire', 'zombie', 'bat', 'spider'],
    'scifi': ['robot', 'alien', 'spaceship', 'space', 'rocket', 'laser', 'ufo', 'android', 'cyborg', 'futuristic'],
    'fantasy': ['dragon', 'wizard', 'magic', 'fairy', 'unicorn', 'castle', 'sword', 'knight', 'elf', 'dwarf'],
    'music': ['music', 'guitar', 'piano', 'drum', 'violin', 'microphone', 'headphone', 'speaker', 'note', 'instrument'],
    'sports': ['ball', 'basketball', 'football', 'soccer', 'tennis', 'golf', 'baseball', 'hockey', 'trophy'],
    'office': ['folder', 'document', 'paper', 'clipboard', 'stapler', 'pencil', 'pen', 'desk', 'briefcase'],
    'kitchen': ['pan', 'pot', 'spoon', 'fork', 'knife', 'bowl', 'plate', 'cup', 'mug', 'cooking', 'chef'],
    'gaming': ['game', 'controller', 'joystick', 'arcade', 'pixel', 'mario', 'nintendo', 'playstation'],
    'military': ['tank', 'soldier', 'army', 'gun', 'rifle', 'helmet', 'camouflage', 'medal', 'grenade'],
    'science': ['microscope', 'telescope', 'atom', 'molecule', 'flask', 'beaker', 'lab', 'scientist', 'dna'],
    'fashion': ['dress', 'shirt', 'pants', 'hat', 'shoe', 'boot', 'glasses', 'jewelry', 'watch', 'purse'],
    'art': ['paint', 'brush', 'canvas', 'palette', 'sculpture', 'drawing', 'sketch', 'frame'],
    'horror': ['blood', 'skull', 'monster', 'demon', 'scary', 'creepy', 'dark', 'evil'],
    'portrait': ['face', 'person', 'man', 'woman', 'boy', 'girl', 'head', 'portrait'],
    'cute': ['cute', 'adorable', 'kawaii', 'smile', 'happy', 'heart', 'bunny', 'kitten', 'puppy'],
    'retro': ['vintage', 'classic', 'old', 'antique', 'retro', 'nostalgic', '80s', '90s'],
}

def extract_themes(description, existing_themes):
    """Extract themes from description text."""
    if not description:
        return existing_themes

    desc_lower = description.lower()
    themes = set(existing_themes) if existing_themes else set()

    # Remove empty strings
    themes.discard('')

    # Check for keyword matches
    for theme, keywords in THEME_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                themes.add(theme)
                break

    return list(themes)

def consolidate_vibe(vibe):
    """Map vibe to core vibe."""
    if not vibe:
        return 'technical'  # default
    return VIBE_MAP.get(vibe, vibe)

def extract_vibes_from_description(description, existing_vibe):
    """Extract multiple vibes from description."""
    if not description:
        return [existing_vibe] if existing_vibe else ['technical']

    desc_lower = description.lower()
    vibes = set()

    # Add existing vibe
    if existing_vibe:
        vibes.add(consolidate_vibe(existing_vibe))

    # Vibe keywords
    vibe_keywords = {
        'cute': ['cute', 'adorable', 'kawaii', 'sweet', 'lovely'],
        'spooky': ['scary', 'creepy', 'dark', 'evil', 'sinister', 'skull', 'ghost', 'monster'],
        'playful': ['fun', 'happy', 'cheerful', 'silly', 'cartoon', 'colorful'],
        'elegant': ['elegant', 'fancy', 'ornate', 'decorative', 'golden', 'royal'],
        'retro': ['vintage', 'classic', 'old', 'antique', 'retro'],
        'minimal': ['simple', 'clean', 'basic', 'plain', 'minimal'],
        'cozy': ['warm', 'cozy', 'home', 'comfort', 'soft'],
        'quirky': ['weird', 'strange', 'unusual', 'odd', 'quirky'],
        'technical': ['computer', 'electronic', 'digital', 'technical', 'mechanical'],
    }

    for vibe, keywords in vibe_keywords.items():
        for keyword in keywords:
            if keyword in desc_lower:
                vibes.add(vibe)
                break

    return list(vibes) if vibes else ['technical']

def consolidate_category(category):
    """Map category to consolidated category."""
    if not category:
        return 'object'  # default
    return CATEGORY_MAP.get(category, category)

def main():
    print("Reassessing taxonomy")
    print("=" * 50)

    # Load tags
    with open(TAGS_FILE) as f:
        data = json.load(f)

    icons = data['icons']
    print(f"Processing {len(icons)} icons")

    # Track changes
    vibe_changes = Counter()
    category_changes = Counter()
    themes_added = 0

    for icon in icons:
        # Consolidate category
        old_cat = icon.get('primary', '')
        new_cat = consolidate_category(old_cat)
        if old_cat != new_cat:
            category_changes[f"{old_cat} -> {new_cat}"] += 1
        icon['primary'] = new_cat

        # Extract multiple vibes from description
        old_vibe = icon.get('vibe', '')
        new_vibes = extract_vibes_from_description(icon.get('description', ''), old_vibe)
        icon['vibes'] = new_vibes  # Now an array
        icon['vibe'] = new_vibes[0] if new_vibes else 'technical'  # Keep primary for backwards compat

        # Extract and clean themes
        old_themes = icon.get('secondary', [])
        new_themes = extract_themes(icon.get('description', ''), old_themes)

        # Remove themes that overlap with vibes
        new_themes = [t for t in new_themes if t not in ['technical', 'cozy', 'minimal', 'spooky', '']]

        if len(new_themes) > len([t for t in old_themes if t]):
            themes_added += 1
        icon['secondary'] = new_themes

        # Clean colors (remove empty)
        icon['colors'] = [c for c in icon.get('colors', []) if c]

    # Report changes
    print(f"\nCategory changes:")
    for change, count in category_changes.most_common():
        print(f"  {change}: {count}")

    print(f"\nVibe consolidations:")
    for change, count in vibe_changes.most_common(20):
        print(f"  {change}: {count}")

    print(f"\nThemes extracted from descriptions: {themes_added}")

    # Show new distribution
    print("\n" + "=" * 50)
    print("NEW DISTRIBUTION:")

    primaries = Counter(i.get('primary') for i in icons)
    print("\nCategories:")
    for cat, count in primaries.most_common():
        print(f"  {cat}: {count}")

    vibes = Counter()
    multi_vibe_count = 0
    for i in icons:
        icon_vibes = i.get('vibes', [i.get('vibe')])
        if len(icon_vibes) > 1:
            multi_vibe_count += 1
        for v in icon_vibes:
            if v:
                vibes[v] += 1
    print(f"\nVibes ({multi_vibe_count} icons have multiple):")
    for vibe, count in vibes.most_common():
        print(f"  {vibe}: {count}")

    themes = Counter()
    for i in icons:
        for t in i.get('secondary', []):
            if t:
                themes[t] += 1
    print("\nThemes:")
    for theme, count in themes.most_common():
        print(f"  {theme}: {count}")

    # Save
    # Preserve deduplication metadata if present
    output_data = {'icons': icons}
    if 'deduplication' in data:
        output_data['deduplication'] = data['deduplication']
    output_data['taxonomy_version'] = 2

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")
    print("To apply: cp public/tags-retagged.json public/tags.json")

if __name__ == "__main__":
    main()
