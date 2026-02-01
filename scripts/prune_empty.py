#!/usr/bin/env python3
"""
Find and remove empty/nearly-empty icons from tags.json.
An icon is considered empty if it has very few non-transparent pixels.
"""

import json
from pathlib import Path
from PIL import Image

ICONS_DIR = Path("/Users/mae/Documents/Inspo space/public/icons/extracted-transparent")
TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/tags.json")

# Minimum non-transparent pixels to be considered valid
MIN_PIXELS = 50

def count_visible_pixels(path):
    """Count pixels that aren't fully transparent."""
    try:
        img = Image.open(path).convert("RGBA")
        pixels = list(img.getdata())
        # Count pixels where alpha > 0
        visible = sum(1 for p in pixels if p[3] > 0)
        return visible
    except Exception as e:
        print(f"  Error reading {path.name}: {e}")
        return 0

def main():
    print("Pruning empty icons from tags.json")
    print("=" * 50)

    # Load tags
    with open(TAGS_FILE) as f:
        data = json.load(f)

    original_count = len(data["icons"])
    print(f"Icons in tags.json: {original_count}")

    # Check each icon
    empty_files = []
    missing_files = []

    for i, icon in enumerate(data["icons"]):
        if i % 500 == 0:
            print(f"Checking {i}/{original_count}...")

        path = ICONS_DIR / icon["file"]

        if not path.exists():
            missing_files.append(icon["file"])
            continue

        visible = count_visible_pixels(path)
        if visible < MIN_PIXELS:
            empty_files.append(icon["file"])

    print(f"\nFound {len(empty_files)} empty icons (< {MIN_PIXELS} visible pixels)")
    print(f"Found {len(missing_files)} missing files")

    if empty_files:
        print("\nSample empty files:")
        for f in empty_files[:10]:
            print(f"  {f}")

    # Remove empty/missing from data
    remove_set = set(empty_files + missing_files)
    data["icons"] = [i for i in data["icons"] if i["file"] not in remove_set]
    data["tagged_files"] = [f for f in data["tagged_files"] if f not in remove_set]
    data["tagged"] = len(data["icons"])

    # Save
    print(f"\nKeeping {len(data['icons'])} icons")

    with open(TAGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print("Done! tags.json updated.")

if __name__ == "__main__":
    main()
