#!/usr/bin/env python3
"""
Add new icons to the archive with basic metadata.

This script copies icons to the public/icons folder and creates entries in
tags.json with basic metadata derived from filenames. It performs perceptual
hash-based deduplication to avoid adding visually identical icons.

No API calls are made - enrichment (descriptions, themes, colors) should be
done separately using enrich_from_metadata.py or vision tagging.

Usage:
    python add_icons_basic.py <new_icons_list.txt>

The input file should contain one icon path per line (output from check_duplicates.py
or a simple `ls` of extracted icons).

Example workflow:
    # 1. Extract icons from source
    python extract_batch.py ~/Downloads/icons ./staging

    # 2. Check for duplicates and get list of truly new icons
    python check_duplicates.py ./staging > truly_new.txt

    # 3. Add the new icons to the archive
    python add_icons_basic.py truly_new.txt

    # 4. Enrich with themes based on collection names
    python enrich_from_metadata.py

Requirements:
    pip install pillow imagehash
"""

import json
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
    import imagehash
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install pillow imagehash")
    sys.exit(1)

# Paths relative to script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
ICONS_DIR = PROJECT_DIR / "public" / "icons"
TAGS_FILE = PROJECT_DIR / "public" / "tags.json"


def get_image_hash(filepath):
    """Get perceptual hash of an image for deduplication.

    Uses average hash with 16x16 resolution for good accuracy.
    Returns None if image can't be processed.
    """
    try:
        img = Image.open(filepath)
        return str(imagehash.average_hash(img, hash_size=16))
    except Exception:
        return None


def get_display_name(filename):
    """Convert filename to human-readable display name.

    Input: "ALIEN-Icons--Facehugger.png"
    Output: "Facehugger"
    """
    # Format: collection--name.png
    if '--' in filename:
        name = filename.split('--', 1)[1]
    else:
        name = filename

    # Remove extension and clean up
    name = name.replace('.png', '')
    name = name.replace('-', ' ').replace('_', ' ')
    # Collapse multiple spaces
    while '  ' in name:
        name = name.replace('  ', ' ')
    return name.strip()


def get_collection(filename):
    """Extract collection name from filename.

    Input: "ALIEN-Icons--Facehugger.png"
    Output: "ALIEN Icons"
    """
    if '--' in filename:
        return filename.split('--')[0].replace('-', ' ')
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python add_icons_basic.py <new_icons_list.txt>")
        print()
        print("The input file should contain one icon path per line.")
        print("Use check_duplicates.py to generate this list.")
        sys.exit(1)

    list_file = Path(sys.argv[1])
    if not list_file.exists():
        print(f"Error: {list_file} not found")
        sys.exit(1)

    # Load existing data
    print("Loading existing hashes...")
    existing_hashes = {}
    for icon_file in ICONS_DIR.glob("*.png"):
        h = get_image_hash(icon_file)
        if h:
            existing_hashes[h] = icon_file.name

    print(f"  {len(existing_hashes)} existing hashes")

    with open(TAGS_FILE) as f:
        tags_data = json.load(f)

    existing_files = {icon['file'] for icon in tags_data['icons']}
    print(f"  {len(existing_files)} existing entries in tags.json")

    # Read list of new icons
    with open(list_file) as f:
        new_paths = [Path(line.strip()) for line in f if line.strip()]

    print(f"\nProcessing {len(new_paths)} new icons...")

    added = 0
    skipped_dup = 0
    skipped_hash = 0

    for icon_path in new_paths:
        if not icon_path.exists():
            continue

        # Check perceptual hash for visual duplicates
        h = get_image_hash(icon_path)
        if h and h in existing_hashes:
            skipped_hash += 1
            continue

        # Check filename
        if icon_path.name in existing_files:
            skipped_dup += 1
            continue

        # Copy file to icons directory
        dest = ICONS_DIR / icon_path.name
        counter = 1
        while dest.exists():
            stem = icon_path.stem
            dest = ICONS_DIR / f"{stem}-{counter}.png"
            counter += 1

        shutil.copy2(icon_path, dest)

        # Create basic metadata entry
        entry = {
            'file': dest.name,
            'display_name': get_display_name(icon_path.name),
            'collection': get_collection(icon_path.name),
            'category': 'object',  # Default, enriched later
            'primary': 'object',
            'themes': [],
            'secondary': [],
            'vibes': ['retro'],
            'vibe': 'retro',
            'colors': [],
            'description': '',
        }

        tags_data['icons'].append(entry)

        if h:
            existing_hashes[h] = dest.name
        existing_files.add(dest.name)
        added += 1

        if added % 100 == 0:
            print(f"  Added {added}...")

    # Save updated tags.json
    print(f"\nSaving tags.json...")
    with open(TAGS_FILE, 'w') as f:
        json.dump(tags_data, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Added: {added}")
    print(f"Skipped (visual duplicate): {skipped_hash}")
    print(f"Skipped (filename exists): {skipped_dup}")
    print(f"Total icons now: {len(tags_data['icons'])}")
    print()
    print("Next step: Run enrich_from_metadata.py to add themes")


if __name__ == "__main__":
    main()
