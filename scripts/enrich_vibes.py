#!/usr/bin/env python3
"""
Enrich vibes based on description/collection/display_name patterns.

Uses word boundaries to avoid false positives.
RULE: NEVER remove tags, only ADD.
"""

import json
import re
from pathlib import Path
from collections import Counter

TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags-enriched.json")
OUTPUT_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags-vibes-enriched.json")

# Patterns that map to vibes - using word boundaries
# Format: vibe -> list of (pattern, description)
VIBE_PATTERNS = {
    'mystical': [
        r'\bwizard\b', r'\bmage\b', r'\bmagic\b', r'\bceltic\b', r'\bcrystal\b',
        r'\borb\b', r'\benchant', r'\bmystic', r'\bpotion\b', r'\bspell\b',
        r'\bwand\b', r'\balchemy\b', r'\brune\b', r'\bdruid\b',
    ],
    'fantasy': [
        r'\bdragon\b', r'\bcastle\b', r'\bknight\b', r'\bsword\b', r'\barmor\b',
        r'\belf\b', r'\bdwarf\b', r'\bgoblin\b', r'\borc\b', r'\bthrone\b',
        r'\bcrown\b', r'\bmedieval\b', r'\bpaladin\b', r'\bwarrior\b',
        r'\brobed figure\b', r'\bwith staff\b',
    ],
    'festive': [
        r'\bbell\b', r'\bbells\b', r'\bribbon\b', r'\bornament\b',
        r'\bcelebrat', r'\bparty\b', r'\bconfetti\b', r'\bballoon\b',
        r'\bgift\b', r'\bpresent\b(?! slide)', r'\bgarland\b', r'\bwreath\b',
    ],
    'heroic': [
        r'\bwarrior\b', r'\bhero\b(?!n)', r'\bshield\b', r'\barmor\b',
        r'\bbrave\b', r'\bsoldier\b', r'\bchampion\b', r'\bviking\b',
        r'\bhelmet\b', r'\bsword and shield\b',
    ],
    'cheerful': [
        r'\brainbow\b', r'\bsun\b(?!glass|day|flower)', r'\bsmil', r'\bhappy\b',
        r'\bsmiley\b', r'\bcolorful\b',
    ],
    'rustic': [
        r'\bwooden\b', r'\bcrate\b', r'\bbasket\b(?!ball)', r'\bbarn\b',
        r'\bfarm\b', r'\bhay\b', r'\bbarrel\b', r'\bfence\b', r'\brope\b',
        r'\bburlap\b', r'\bwoven\b',
    ],
    'mysterious': [
        r'\bmystery\b', r'\bsecret\b', r'\bhidden\b', r'\bshadow\b',
        r'\bcloak\b', r'\bhooded\b', r'\bmask\b', r'\benigma\b',
    ],
    'ancient': [
        r'\bancient\b', r'\bruin\b', r'\btemple\b', r'\bpyramid\b',
        r'\bartifact\b', r'\btomb\b', r'\bpharaoh\b', r'\bmummy\b',
        r'\bhieroglyphic\b', r'\bstone tablet\b',
    ],
    'whimsical': [
        r'\bmushroom\b', r'\bfairy\b', r'\bpixie\b', r'\bgnome\b',
        r'\bwhims', r'\bfantastic', r'\bmagical forest\b',
    ],
    'fierce': [
        r'\bbeast\b', r'\bmonster\b', r'\bdemon\b', r'\bfierce\b',
        r'\broar\b', r'\bfang\b', r'\bclaw\b(?!ed)', r'\bpredator\b',
        r'\bdevil\b', r'\baggressiv',
    ],
    'dramatic': [
        r'\bflame\b', r'\bflames\b', r'\bfire\b(?! extinguisher| hydrant)',
        r'\bexplosion\b', r'\blightning\b', r'\bstorm\b', r'\binferno\b',
        r'\bblaze\b', r'\bburning\b',
    ],
    'patriotic': [
        r'\bamerican flag\b', r'\busa\b', r'\bpatriotic\b', r'\bnational flag\b',
        r'\bstars and stripes\b', r'\bunion jack\b',
    ],
    'majestic': [
        r'\bking\b(?! o beasts)', r'\bqueen\b', r'\broyal\b', r'\bthrone\b',
        r'\bpalace\b', r'\bmajestic\b', r'\bnoble\b', r'\bregal\b',
        r'\bemperor\b', r'\bempress\b',
    ],
    'adventurous': [
        r'\bexplorer\b', r'\badventure\b', r'\bcompass\b', r'\btreasure\b',
        r'\bpirate\b', r'\bjourney\b', r'\bexpedition\b', r'\bsafari\b',
    ],
    'cozy': [
        r'\bfireplace\b', r'\bcottage\b', r'\bcandle\b(?!stick)',
        r'\bblanket\b', r'\bwarm\b', r'\bcocoa\b', r'\bhot chocolate\b',
        r'\bfuzzy\b', r'\bsoft\b', r'\bcushion\b',
    ],
}

# Collection patterns -> vibes
COLLECTION_VIBE_PATTERNS = {
    'mystical': [r'celtic', r'druid', r'magic'],
    'fantasy': [r'knight', r'medieval', r'dragon', r'diablo'],
    'festive': [r'christmas', r'holiday', r'celebration'],
    'fierce': [r'monster', r'beast', r'horror'],
    'adventurous': [r'pirate', r'treasure', r'explorer'],
    'whimsical': [r'mushroom', r'fairy', r'wonderland'],
}


def matches_patterns(text, patterns):
    """Check if text matches any pattern."""
    if not text:
        return False
    text_lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def main():
    print("=" * 60)
    print("Enriching vibes from descriptions and collections")
    print("=" * 60)
    print("\nRULE: Only ADDING vibes, never removing.\n")

    with open(TAGS_FILE) as f:
        data = json.load(f)

    icons = data['icons']
    print(f"Processing {len(icons)} icons\n")

    vibes_added = Counter()
    icons_enriched = 0

    for icon in icons:
        desc = icon.get('description', '')
        name = icon.get('display_name', '')
        collection = icon.get('collection', '')

        existing_vibes = set(icon.get('vibes', []))
        new_vibes = set()

        # Check description and display name
        combined_text = f"{desc} {name}"

        for vibe, patterns in VIBE_PATTERNS.items():
            if vibe in existing_vibes:
                continue
            if matches_patterns(combined_text, patterns):
                new_vibes.add(vibe)

        # Check collection
        for vibe, patterns in COLLECTION_VIBE_PATTERNS.items():
            if vibe in existing_vibes:
                continue
            if matches_patterns(collection, patterns):
                new_vibes.add(vibe)

        # Apply new vibes
        if new_vibes:
            icons_enriched += 1
            icon['vibes'] = sorted(list(existing_vibes | new_vibes))
            icon['vibe'] = icon['vibes'][0]  # backwards compat
            for v in new_vibes:
                vibes_added[v] += 1

    # Report
    print(f"Icons enriched: {icons_enriched} / {len(icons)}")

    print(f"\nVibes added ({sum(vibes_added.values())} total):")
    for vibe, count in vibes_added.most_common():
        print(f"  {vibe}: +{count}")

    # Final vibe distribution
    print("\n" + "=" * 60)
    print("FINAL VIBE DISTRIBUTION:")

    all_vibes = Counter()
    for icon in icons:
        for v in icon.get('vibes', []):
            all_vibes[v] += 1

    for vibe, count in all_vibes.most_common():
        print(f"  {vibe}: {count}")

    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")
    print("To apply: cp public/tags-vibes-enriched.json public/tags.json")


if __name__ == "__main__":
    main()
