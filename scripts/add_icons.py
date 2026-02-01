#!/usr/bin/env python3
"""
Add new icons to the archive.

Flow:
1. Takes a folder of new icon PNGs
2. Checks for duplicates against existing icons (using perceptual hash)
3. Uses Claude vision API to tag them (category, themes, vibes, description)
4. Adds non-duplicates to tags.json

Usage:
    python add_icons.py /path/to/new/icons/

Requirements:
    pip install anthropic pillow imagehash
    export ANTHROPIC_API_KEY=your_key
"""

import os
import sys
import json
import shutil
import base64
from pathlib import Path
from collections import defaultdict

from PIL import Image
import imagehash
import anthropic

# Paths
ICONS_DIR = Path("/Users/mae/Documents/icon-archaeology/public/icons")
TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")

# Valid categories
CATEGORIES = ['object', 'character', 'symbol', 'ui', 'text']

# Core vibes
VIBES = ['technical', 'playful', 'cozy', 'minimal', 'retro', 'elegant', 'quirky', 'spooky', 'cute']

TAGGING_PROMPT = """Analyze this classic Mac OS icon and provide tags in JSON format.

Categories (pick ONE that best fits):
- object: things, items, tools, food, hardware, vehicles
- character: people, animals, creatures, faces
- symbol: abstract shapes, logos, icons, arrows
- ui: interface elements, folders, buttons, windows
- text: primarily letters/words

Vibes (pick 1-3 that describe the aesthetic feeling):
technical, playful, cozy, minimal, retro, elegant, quirky, spooky, cute

Themes (pick all that apply - subject matter):
food, drink, japanese, christmas, halloween, scifi, fantasy, music, sports, office, kitchen, gaming, military, science, fashion, art, horror, animal, nature, vehicle, hardware, communication, portrait, etc.

Colors (list the main colors visible):
red, orange, yellow, green, blue, purple, pink, brown, black, white, gray

Respond with ONLY valid JSON:
{
  "category": "object",
  "vibes": ["playful", "retro"],
  "themes": ["food", "japanese"],
  "colors": ["red", "yellow"],
  "description": "brief 3-8 word description of what the icon depicts"
}"""

def get_image_hash(filepath):
    """Get perceptual hash of an image."""
    try:
        img = Image.open(filepath)
        return str(imagehash.average_hash(img, hash_size=16))
    except Exception as e:
        print(f"  Error hashing {filepath}: {e}")
        return None

def load_existing_hashes():
    """Load hashes of existing icons."""
    print("Loading existing icon hashes...")
    hashes = {}

    for icon_file in ICONS_DIR.glob("*.png"):
        h = get_image_hash(icon_file)
        if h:
            hashes[h] = icon_file.name

    print(f"  Loaded {len(hashes)} existing hashes")
    return hashes

def encode_image_base64(filepath):
    """Encode image as base64 for API."""
    with open(filepath, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")

def tag_icon(client, filepath):
    """Use Claude vision to tag a single icon."""
    try:
        image_data = encode_image_base64(filepath)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        }
                    },
                    {
                        "type": "text",
                        "text": TAGGING_PROMPT
                    }
                ]
            }]
        )

        # Parse JSON response
        text = response.content[0].text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        data = json.loads(text)

        # Validate category
        if data.get('category') not in CATEGORIES:
            data['category'] = 'object'

        # Validate vibes
        data['vibes'] = [v for v in data.get('vibes', []) if v in VIBES] or ['technical']

        return data

    except Exception as e:
        print(f"  Error tagging: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python add_icons.py /path/to/new/icons/")
        print("\nThis script will:")
        print("1. Check new icons for duplicates")
        print("2. Tag non-duplicates using Claude vision API")
        print("3. Copy them to the icons folder")
        print("4. Add them to tags.json")
        sys.exit(1)

    new_icons_dir = Path(sys.argv[1])
    if not new_icons_dir.exists():
        print(f"Error: {new_icons_dir} does not exist")
        sys.exit(1)

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    print("=" * 50)
    print("Add New Icons")
    print("=" * 50)

    # Load existing data
    existing_hashes = load_existing_hashes()

    with open(TAGS_FILE) as f:
        tags_data = json.load(f)

    existing_files = {icon['file'] for icon in tags_data['icons']}
    print(f"Existing icons in tags.json: {len(existing_files)}")

    # Find new icons
    new_icons = list(new_icons_dir.glob("*.png"))
    print(f"\nFound {len(new_icons)} PNG files in {new_icons_dir}")

    # Check for duplicates
    print("\nChecking for duplicates...")
    to_add = []
    duplicates = []

    for icon_path in new_icons:
        h = get_image_hash(icon_path)
        if not h:
            continue

        if h in existing_hashes:
            duplicates.append((icon_path.name, existing_hashes[h]))
        elif icon_path.name in existing_files:
            duplicates.append((icon_path.name, "filename exists"))
        else:
            to_add.append(icon_path)

    print(f"\nDuplicates found: {len(duplicates)}")
    for new, existing in duplicates[:10]:
        print(f"  {new} -> {existing}")
    if len(duplicates) > 10:
        print(f"  ... and {len(duplicates) - 10} more")

    print(f"\nNew icons to add: {len(to_add)}")

    if not to_add:
        print("No new icons to add!")
        sys.exit(0)

    # Confirm
    response = input("\nProceed with tagging and adding? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        sys.exit(0)

    # Initialize Claude client
    client = anthropic.Anthropic()

    # Tag and add each icon
    print("\nTagging and adding icons...")
    added = 0

    for i, icon_path in enumerate(to_add):
        print(f"\n[{i+1}/{len(to_add)}] {icon_path.name}")

        # Tag with Claude
        tags = tag_icon(client, icon_path)
        if not tags:
            print("  Skipping (tagging failed)")
            continue

        print(f"  Category: {tags['category']}")
        print(f"  Vibes: {tags['vibes']}")
        print(f"  Themes: {tags.get('themes', [])}")
        print(f"  Description: {tags.get('description', '')}")

        # Copy to icons folder
        dest_path = ICONS_DIR / icon_path.name
        if dest_path.exists():
            # Add suffix to avoid overwrite
            stem = icon_path.stem
            suffix = 1
            while dest_path.exists():
                dest_path = ICONS_DIR / f"{stem}-{suffix}.png"
                suffix += 1

        shutil.copy2(icon_path, dest_path)
        print(f"  Copied to: {dest_path.name}")

        # Add to tags
        icon_entry = {
            'file': dest_path.name,
            'category': tags['category'],
            'primary': tags['category'],  # backwards compat
            'vibes': tags['vibes'],
            'vibe': tags['vibes'][0],  # backwards compat
            'themes': tags.get('themes', []),
            'secondary': tags.get('themes', []),  # backwards compat
            'colors': tags.get('colors', []),
            'description': tags.get('description', ''),
            'display_name': icon_path.stem.replace('-', ' ').replace('_', ' '),
        }

        tags_data['icons'].append(icon_entry)
        added += 1

        # Update hash cache
        h = get_image_hash(dest_path)
        if h:
            existing_hashes[h] = dest_path.name

    # Save updated tags
    print(f"\nSaving {len(tags_data['icons'])} icons to tags.json...")
    with open(TAGS_FILE, 'w') as f:
        json.dump(tags_data, f, indent=2)

    print(f"\nDone! Added {added} new icons.")
    print(f"Total icons now: {len(tags_data['icons'])}")

if __name__ == "__main__":
    main()
