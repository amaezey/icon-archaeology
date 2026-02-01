#!/usr/bin/env python3
"""
Deduplicate icons using image hashing.
Groups identical/near-identical icons and merges their metadata.
"""

import json
import hashlib
from pathlib import Path
from collections import defaultdict
from PIL import Image
import imagehash

ICONS_DIR = Path("/Users/mae/Documents/icon-archaeology/public/icons")
TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")
OUTPUT_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags-deduped.json")

def get_image_hash(filepath):
    """Get perceptual hash of an image."""
    try:
        img = Image.open(filepath)
        # Use average hash - good for detecting identical/near-identical images
        return str(imagehash.average_hash(img, hash_size=16))
    except Exception as e:
        print(f"Error hashing {filepath}: {e}")
        return None

def score_name(name):
    """Score a display name - higher is better."""
    if not name or name.strip() == '' or name == '?':
        return 0
    # Penalize names that are just dashes/numbers
    if name.replace('-', '').replace(' ', '').isdigit():
        return 1
    # Penalize very short names
    if len(name) < 3:
        return 2
    # Penalize names starting with special chars
    if name[0] in '-_./':
        return 3
    # Prefer names with spaces (more readable)
    if ' ' in name:
        return 10
    return 5

def merge_icons(icons):
    """Merge multiple icon entries into one, keeping best metadata."""
    if len(icons) == 1:
        return icons[0]

    # Sort by name quality to pick best
    icons_sorted = sorted(icons, key=lambda i: score_name(i.get('display_name', '')), reverse=True)
    best = icons_sorted[0].copy()

    # Collect all unique values from duplicates
    all_collections = set()
    all_paths = []
    all_secondary = set()
    all_colors = set()
    all_files = []

    for icon in icons:
        if icon.get('collection'):
            all_collections.add(icon['collection'])
        if icon.get('path'):
            all_paths.append(icon['path'])
        if icon.get('secondary'):
            all_secondary.update(icon['secondary'])
        if icon.get('colors'):
            all_colors.update(icon['colors'])
        all_files.append(icon['file'])

    # Update best with merged data
    best['secondary'] = list(all_secondary) if all_secondary else best.get('secondary', [])
    best['colors'] = list(all_colors) if all_colors else best.get('colors', [])
    best['duplicate_files'] = all_files  # Track which files were merged
    best['collections'] = list(all_collections) if len(all_collections) > 1 else None

    return best

def main():
    print("Deduplicating icons")
    print("=" * 50)

    # Load tags
    with open(TAGS_FILE) as f:
        data = json.load(f)

    icons = data['icons']
    print(f"Starting with {len(icons)} icons")

    # Hash all icons
    print("\nHashing images...")
    hash_to_icons = defaultdict(list)

    for i, icon in enumerate(icons):
        if i % 1000 == 0:
            print(f"  {i}/{len(icons)}...")

        filepath = ICONS_DIR / icon['file']
        if not filepath.exists():
            continue

        img_hash = get_image_hash(filepath)
        if img_hash:
            hash_to_icons[img_hash].append(icon)

    print(f"\nFound {len(hash_to_icons)} unique hashes")

    # Count duplicates
    dup_groups = {h: icons for h, icons in hash_to_icons.items() if len(icons) > 1}
    total_dups = sum(len(icons) - 1 for icons in dup_groups.values())
    print(f"Duplicate groups: {len(dup_groups)}")
    print(f"Total duplicates to remove: {total_dups}")

    # Show some examples
    print("\nSample duplicate groups:")
    for h, group in list(dup_groups.items())[:5]:
        names = [i.get('display_name', i['file'])[:30] for i in group]
        print(f"  {len(group)} copies: {names}")

    # Merge duplicates
    print("\nMerging duplicates...")
    deduped = []
    for img_hash, group in hash_to_icons.items():
        merged = merge_icons(group)
        deduped.append(merged)

    print(f"\nResult: {len(deduped)} unique icons (removed {len(icons) - len(deduped)})")

    # Save
    output_data = {
        'icons': deduped,
        'deduplication': {
            'original_count': len(icons),
            'unique_count': len(deduped),
            'removed': len(icons) - len(deduped)
        }
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")
    print("\nTo apply: cp public/tags-deduped.json public/tags.json")

if __name__ == "__main__":
    main()
