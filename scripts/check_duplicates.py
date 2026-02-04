#!/usr/bin/env python3
"""
Check new icons for duplicates against the existing archive.

This script compares icons in a staging folder against the archive using
perceptual hashing. It reports which icons are truly new vs duplicates,
broken down by collection.

Use this before adding icons to avoid bloating the archive with duplicates.

Usage:
    python check_duplicates.py <new_icons_dir>
    python check_duplicates.py <new_icons_dir> --output truly_new.txt

Examples:
    # Just report duplicates
    python check_duplicates.py ./staging

    # Save list of new icons to a file for add_icons_basic.py
    python check_duplicates.py ./staging --output truly_new.txt
    python add_icons_basic.py truly_new.txt

Requirements:
    pip install pillow imagehash
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

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
    """Get perceptual hash of an image."""
    try:
        img = Image.open(filepath)
        return str(imagehash.average_hash(img, hash_size=16))
    except Exception as e:
        print(f"  Error hashing {filepath}: {e}", file=sys.stderr)
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Check for duplicates before adding icons",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./staging
  %(prog)s ./staging --output truly_new.txt
        """
    )
    parser.add_argument("new_icons_dir", help="Path to folder with new icons")
    parser.add_argument("--output", "-o", help="Write truly new icon paths to file")
    args = parser.parse_args()

    new_dir = Path(args.new_icons_dir)
    if not new_dir.is_dir():
        print(f"Error: {new_dir} is not a directory")
        sys.exit(1)

    print("Loading existing icon hashes...")
    existing_hashes = {}
    for icon_file in ICONS_DIR.glob("*.png"):
        h = get_image_hash(icon_file)
        if h:
            existing_hashes[h] = icon_file.name
    print(f"  Loaded {len(existing_hashes)} existing hashes")

    # Load existing filenames
    with open(TAGS_FILE) as f:
        tags_data = json.load(f)
    existing_files = {icon['file'] for icon in tags_data['icons']}

    # Check new icons
    new_icons = list(new_dir.glob("*.png"))
    print(f"\nChecking {len(new_icons)} new icons...")

    duplicates = []
    truly_new = []

    for icon_path in new_icons:
        h = get_image_hash(icon_path)
        if not h:
            continue

        if h in existing_hashes:
            duplicates.append((icon_path, existing_hashes[h], "visual match"))
        elif icon_path.name in existing_files:
            duplicates.append((icon_path, "same filename", "filename"))
        else:
            truly_new.append(icon_path)

    # Summarize by collection
    new_by_collection = defaultdict(list)
    for path in truly_new:
        collection = path.name.split('--')[0] if '--' in path.name else 'unknown'
        new_by_collection[collection].append(path)

    dup_by_collection = defaultdict(list)
    for path, match, reason in duplicates:
        collection = path.name.split('--')[0] if '--' in path.name else 'unknown'
        dup_by_collection[collection].append(path.name)

    # Print report
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Total checked: {len(new_icons)}")
    print(f"Duplicates:    {len(duplicates)}")
    print(f"Truly new:     {len(truly_new)}")

    print(f"\n{'='*60}")
    print(f"NEW ICONS BY COLLECTION")
    print(f"{'='*60}")
    for collection in sorted(new_by_collection.keys()):
        count = len(new_by_collection[collection])
        print(f"  {collection}: {count}")

    if dup_by_collection:
        print(f"\n{'='*60}")
        print(f"DUPLICATES BY COLLECTION")
        print(f"{'='*60}")
        for collection in sorted(dup_by_collection.keys()):
            count = len(dup_by_collection[collection])
            print(f"  {collection}: {count}")

    # Sample new icons
    if truly_new:
        print(f"\n{'='*60}")
        print(f"SAMPLE NEW ICONS (first 20)")
        print(f"{'='*60}")
        for path in truly_new[:20]:
            print(f"  {path.name}")

    # Write output file if requested
    if args.output and truly_new:
        with open(args.output, 'w') as f:
            for path in truly_new:
                f.write(f"{path}\n")
        print(f"\nWrote {len(truly_new)} paths to {args.output}")
        print(f"Next: python add_icons_basic.py {args.output}")


if __name__ == "__main__":
    main()
