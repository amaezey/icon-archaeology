#!/usr/bin/env python3
"""
Add original display names to tags.json by matching against source directories.
Uses multiple strategies to match extracted filenames back to originals.
"""

import os
import json
from pathlib import Path

SOURCE_DIR = Path("/Users/mae/Documents/Inspo space/Media/Icons")
TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/tags.json")

def sanitize_name(name):
    return ''.join(c if c.isalnum() or c in '-_' else '-' for c in name.lower()).strip('-')

def build_name_lookup():
    """Build lookup from sanitized icon name to original info."""
    # Map: sanitized_name -> {display_name, path}
    lookup = {}

    for icon_dir in SOURCE_DIR.rglob('*'):
        if not icon_dir.is_dir():
            continue
        icon_file = icon_dir / "Icon\r"
        rsrc_path = str(icon_file) + "/..namedfork/rsrc"
        if not os.path.exists(rsrc_path):
            continue

        rel_parts = icon_dir.relative_to(SOURCE_DIR).parts
        sanitized = sanitize_name(icon_dir.name)

        # Also build category--name key for direct matching
        if len(rel_parts) >= 2:
            category = sanitize_name(icon_dir.parent.name)
            full_key = f"{category}--{sanitized}"
            lookup[full_key] = {
                'display_name': icon_dir.name,
                'collection': icon_dir.parent.name,
                'path': list(rel_parts)
            }

        # Store by just sanitized name too (for fallback matching)
        if sanitized not in lookup:
            lookup[sanitized] = {
                'display_name': icon_dir.name,
                'collection': icon_dir.parent.name if len(rel_parts) >= 2 else '',
                'path': list(rel_parts)
            }

    return lookup

def match_filename(filename, lookup):
    """Try to match an extracted filename to an original."""
    base = filename.replace('.png', '')

    # Strategy 1: Direct match (category--name format)
    if base in lookup:
        return lookup[base]

    # Strategy 2: Remove ---XXXXX suffix and try direct match
    if '---' in base:
        cleaned = base.rsplit('---', 1)[0]
        if cleaned in lookup:
            return lookup[cleaned]

    # Strategy 3: Split on -- and try each part
    if '--' in base:
        parts = base.split('--')
        # Try from the end (icon name is usually last)
        for part in reversed(parts):
            part = part.rstrip('-').lstrip('-')  # Clean up extra dashes
            if part and part in lookup:
                return lookup[part]

    # Strategy 4: Remove trailing ---XXXXX and try parts
    if '---' in base:
        cleaned = base.rsplit('---', 1)[0]
        if '--' in cleaned:
            parts = cleaned.split('--')
            for part in reversed(parts):
                part = part.rstrip('-').lstrip('-')
                if part and part in lookup:
                    return lookup[part]
        elif cleaned in lookup:
            return lookup[cleaned]

    # Strategy 5: Just the base name after all cleaning
    cleaned = base
    for suffix in ['---item-icon', '--item-icon', '-item-icon']:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)]
    cleaned = cleaned.rstrip('-0123456789').rstrip('-')
    if cleaned in lookup:
        return lookup[cleaned]

    return None

def main():
    print("Adding display names to tags.json")
    print("=" * 50)

    print("Building name lookup from source directories...")
    lookup = build_name_lookup()
    print(f"Built lookup with {len(lookup)} entries")

    # Load tags
    with open(TAGS_FILE) as f:
        tags = json.load(f)

    # Match and update icons
    matched = 0
    unmatched = []

    for icon in tags['icons']:
        result = match_filename(icon['file'], lookup)
        if result:
            icon['display_name'] = result['display_name']
            icon['collection'] = result['collection']
            icon['path'] = result['path']
            matched += 1
        else:
            unmatched.append(icon['file'])

    print(f"\nMatched: {matched}/{len(tags['icons'])}")
    print(f"Unmatched: {len(unmatched)}")

    if unmatched:
        print("\nSample unmatched:")
        for f in unmatched[:10]:
            print(f"  {f}")

    # Save
    with open(TAGS_FILE, 'w') as f:
        json.dump(tags, f, indent=2)

    print("\nDone!")

if __name__ == "__main__":
    main()
