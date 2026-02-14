#!/usr/bin/env python3
"""
Add original display names to tags.json by matching against source directories.
Uses multiple strategies to match extracted filenames back to originals.
"""

import os
import json
from pathlib import Path

SOURCE_DIRS = [
    Path("/Users/mae/Documents/icon-archaeology/sources"),
    Path("/Users/mae/Documents/More icons to process"),
    Path("/Users/mae/Documents/More icons to process/untitled folder"),
]
TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")

def sanitize_name(name):
    return ''.join(c if c.isalnum() or c in '-_' else '-' for c in name.lower()).strip('-')

def build_name_lookup():
    """Build lookup from sanitized icon name to original info."""
    # Map: sanitized_name -> {display_name, path}
    lookup = {}

    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            continue

        for icon_dir in source_dir.rglob('*'):
            if not icon_dir.is_dir():
                continue

            # Check for Icon\r files (structured format)
            icon_file = icon_dir / "Icon\r"
            rsrc_path = str(icon_file) + "/..namedfork/rsrc"
            has_icon_cr = os.path.exists(rsrc_path)

            # Also check for individual files with resource forks
            has_rsrc_files = False
            if not has_icon_cr:
                for item in icon_dir.iterdir():
                    if item.is_file() and not item.name.startswith('.'):
                        item_rsrc = str(item) + "/..namedfork/rsrc"
                        if os.path.exists(item_rsrc):
                            has_rsrc_files = True
                            break

            if not has_icon_cr and not has_rsrc_files:
                continue

            rel_parts = icon_dir.relative_to(source_dir).parts
            sanitized = sanitize_name(icon_dir.name)

            # Build category--name key for direct matching
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

            # For individual files inside this dir, add their names too
            if has_rsrc_files:
                collection_name = icon_dir.name
                for item in icon_dir.iterdir():
                    if item.is_file() and not item.name.startswith('.') and item.name != 'Icon\r':
                        item_sanitized = sanitize_name(item.name)
                        coll_sanitized = sanitize_name(collection_name)
                        full_key = f"{coll_sanitized}--{item_sanitized}"
                        if full_key not in lookup:
                            lookup[full_key] = {
                                'display_name': item.name,
                                'collection': collection_name,
                                'path': list(rel_parts) + [item.name]
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
