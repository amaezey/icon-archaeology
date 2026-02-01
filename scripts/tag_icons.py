#!/usr/bin/env python3
"""
Batch-tag icons using Claude's vision API.

Each API call is independent - no context accumulation between calls.
Progress is saved after each batch, so you can interrupt and resume.

Usage:
    export ANTHROPIC_API_KEY=your_key  # or use ~/.anthropic/api_key
    python tag_icons.py
"""

import anthropic
import base64
import json
import os
import sys
from pathlib import Path
from time import sleep

# Paths (hardcoded for this project)
ICONS_DIR = Path("/Users/mae/Documents/Inspo space/public/icons/extracted-transparent")
TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/tags.json")

# Config
BATCH_SIZE = 10  # Stay under API limits
MODEL = "claude-sonnet-4-20250514"

TAXONOMY = {
    "primary": ["food", "character", "animal", "folder", "hardware", "ui", "object", "vehicle", "nature", "symbol", "text"],
    "secondary": ["cute", "retro", "holiday", "christmas", "gaming", "japanese", "portrait", "scifi", "fantasy", "horror", "music", "art", "sports", "kitchen", "office", "science", "military", "fashion"],
    "vibes": ["playful", "technical", "spooky", "cozy", "elegant", "quirky", "minimal", "retro"]
}

TAXONOMY_PROMPT = """Analyze these classic Mac OS icons and tag each one.

For each icon, provide:
1. **primary**: Main category (pick ONE):
   - food (meals, ingredients, desserts, drinks)
   - character (people, cartoon characters, mascots, portraits)
   - animal (creatures, pets, wildlife)
   - folder (Mac folders, directories)
   - hardware (computers, consoles, peripherals, devices)
   - ui (interface elements, controls, system icons, buttons)
   - object (misc physical things, tools, household items)
   - vehicle (cars, ships, planes, spacecraft)
   - nature (plants, weather, landscapes, planets)
   - symbol (flags, logos, abstract shapes, icons)
   - text (attribution, copyright, mostly text)

2. **secondary**: Additional tags (pick 0-3 from):
   - cute, retro, holiday, christmas, gaming, japanese,
   - portrait, scifi, fantasy, horror, music, art, sports,
   - kitchen, office, science, military, fashion

3. **colors**: 1-2 dominant colors (lowercase)

4. **vibe**: One word (playful, technical, spooky, cozy, elegant, quirky, minimal, retro)

Respond with JSON array, one object per icon in order shown:
[{"file": "filename.png", "primary": "...", "secondary": ["..."], "colors": ["..."], "vibe": "..."}]

Only output the JSON array, no other text."""


def load_image_as_base64(path):
    """Load image and convert to base64."""
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def load_tags():
    """Load existing tags or create initial structure."""
    if TAGS_FILE.exists():
        with open(TAGS_FILE) as f:
            return json.load(f)
    return {
        "version": 1,
        "total": 0,
        "tagged": 0,
        "taxonomy": TAXONOMY,
        "tagged_files": [],
        "icons": []
    }


def save_tags(data):
    """Save tags atomically."""
    tmp = TAGS_FILE.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    tmp.rename(TAGS_FILE)


def tag_batch(client, icon_paths):
    """Tag a batch of icons using Claude's vision."""
    content = []
    filenames = []

    for path in icon_paths:
        filename = path.name
        filenames.append(filename)

        try:
            image_data = load_image_as_base64(path)
            content.append({
                "type": "text",
                "text": f"Icon {len(filenames)}: {filename}"
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_data
                }
            })
        except Exception as e:
            print(f"  Warning: Could not load {filename}: {e}")
            continue

    content.append({
        "type": "text",
        "text": TAXONOMY_PROMPT
    })

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": content}]
    )

    # Parse JSON from response
    response_text = response.content[0].text.strip()

    # Handle potential markdown code blocks
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    tags = json.loads(response_text)

    # Ensure filenames match (use our filenames, not what model returned)
    for i, tag in enumerate(tags):
        if i < len(filenames):
            tag["file"] = filenames[i]

    return tags


def main():
    print("Icon Tagger - Using Anthropic API directly")
    print("=" * 50)

    # Initialize client
    client = anthropic.Anthropic()

    # Load current state
    tags = load_tags()

    # Get all PNG files
    all_files = sorted(list(ICONS_DIR.glob("*.png")))
    tags["total"] = len(all_files)

    # Build set of already-tagged files
    tagged_set = set(tags.get("tagged_files", []))

    # Also check icons array for backwards compatibility
    for icon in tags.get("icons", []):
        tagged_set.add(icon["file"])

    # Ensure tagged_files is in sync
    tags["tagged_files"] = sorted(list(tagged_set))

    # Find remaining files
    remaining = [f for f in all_files if f.name not in tagged_set]

    print(f"Total icons: {len(all_files)}")
    print(f"Already tagged: {len(tagged_set)}")
    print(f"Remaining: {len(remaining)}")
    print()

    if not remaining:
        print("All icons already tagged!")
        return

    # Process in batches
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
    batch_num = 0

    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i:i + BATCH_SIZE]
        batch_num += 1

        print(f"Batch {batch_num}/{total_batches}: Processing {len(batch)} icons...", end=" ", flush=True)

        try:
            results = tag_batch(client, batch)

            # Update tags
            for icon_data in results:
                filename = icon_data["file"]
                if filename not in tagged_set:
                    tags["tagged_files"].append(filename)
                    tags["icons"].append(icon_data)
                    tagged_set.add(filename)

            tags["tagged"] = len(tags["tagged_files"])
            save_tags(tags)

            print(f"Done. Progress: {tags['tagged']}/{tags['total']}")

            # Small delay to be nice to API
            if batch_num < total_batches:
                sleep(0.5)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print("Skipping batch, will retry on next run...")
            continue

        except anthropic.APIError as e:
            print(f"API error: {e}")
            if "rate" in str(e).lower():
                print("Rate limited. Waiting 30s...")
                sleep(30)
            else:
                print("Waiting 5s before retry...")
                sleep(5)
            continue

        except KeyboardInterrupt:
            print("\nInterrupted. Progress saved.")
            save_tags(tags)
            sys.exit(0)

    print()
    print(f"Complete! Tagged {tags['tagged']}/{tags['total']} icons.")


if __name__ == "__main__":
    main()
