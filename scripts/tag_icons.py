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
ICONS_DIR = Path("/Users/mae/Documents/icon-archaeology/public/icons")
TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")

# Config
BATCH_SIZE = 10  # Stay under API limits
MODEL = "claude-sonnet-4-20250514"

CATEGORIES = ["character", "food", "hardware", "object", "symbol"]

# Existing tags in the gallery — use these plus invent new ones where needed
KNOWN_TAGS = [
    "3d", "60s", "90s", "abstract", "adventure", "advertising", "aeonflux", "alien",
    "american", "ancient", "animal", "animaniacs", "animation", "anime", "apple",
    "aqua", "aquarium", "archie", "art", "astronomy", "audio", "australia", "autumn",
    "aviation", "bakery", "batman", "beatles", "bento", "book", "botanical", "bread",
    "breakfast", "british", "cafe", "cake", "candy", "cartoon", "cat", "celtic",
    "cereal", "charliebrown", "cheese", "children", "chinese", "christmas", "cinema",
    "citrus", "classic", "claymation", "cleaning", "climbing", "clone", "coatofarms",
    "coffee", "cold", "comics", "communication", "cooking", "copland", "cowboy",
    "creative", "creature", "cultural", "curry", "cute", "czech", "dairy", "dc",
    "deli", "design", "dessert", "diablo", "dinner", "disney", "donuts", "dreamcast",
    "drink", "drseuss", "euro2000", "european", "eworld", "fall", "fantasy", "fashion",
    "fastfood", "february", "fighting", "film", "fish", "fishing", "flintstones",
    "flowers", "folder", "food", "football", "fox", "fruit", "fujiya", "furby",
    "gaming", "garfield", "geometric", "glossy", "graffiti", "guitar", "haagendazs",
    "halloween", "handdrawn", "handheld", "hannabarbera", "hardware", "healthy",
    "heraldry", "hiking", "holiday", "horror", "household", "humor", "ibook",
    "icecream", "illustration", "imac", "indigenous", "industrial", "insignia",
    "instrument", "interface", "internet", "irish", "italian", "japanese", "jleague",
    "kaiju", "katsu", "kids", "kitchen", "korean", "laptop", "looneytunes", "love",
    "lucasfilm", "lure", "m68k", "mac", "macos", "manga", "matrix", "meal", "mecha",
    "medieval", "military", "minimal", "monster", "morning", "mortalkombat", "motorola",
    "mountain", "mtv", "muppets", "music", "mystery", "nasa", "nature", "newton",
    "newyear", "nickelodeon", "nintendo", "noodles", "nostalgia", "october", "office",
    "okashi", "olympics", "online", "osechi", "osx", "outdoor", "palm", "pbs", "pda",
    "peanuts", "pet", "pie", "pizza", "planets", "plant", "pokemon", "popeye",
    "portrait", "powerpc", "premierleague", "produce", "quiet", "renandstimpy",
    "retro", "robot", "rpg", "science", "scifi", "season", "sega", "seriea",
    "sesamestreet", "simpsons", "sketch", "snacks", "snow", "soccer", "sonic", "sony",
    "southamerican", "space", "speedracer", "spooky", "sports", "spring", "startrek",
    "starwars", "stationery", "storage", "stpatricks", "strategy", "streetfood",
    "studio", "summer", "superhero", "sushi", "sweets", "sydney2000", "symbol",
    "tea", "technical", "thunderbirds", "tokusatsu", "tools", "toy", "traditional",
    "tv", "ui", "ultraman", "urban", "valentine", "valentines", "vegetables",
    "vegetarian", "vehicle", "video", "videogame", "vintage", "wagashi",
    "wallaceandgromit", "warehouse", "warnerbros", "wb", "western", "winter",
    "writing", "yosemite"
]

TAXONOMY_PROMPT = """Analyze these classic Mac OS icons and tag each one.

For each icon, provide:
1. **description**: Brief phrase (3-8 words) describing WHAT the icon depicts. Be specific and literal.
   Examples: "yellow smiley face with sunglasses", "blue folder with red apple logo", "cartoon cat face winking"

2. **category**: Main category (pick exactly ONE):
   - character (people, cartoon characters, mascots, portraits, animals, creatures)
   - food (meals, ingredients, desserts, drinks, kitchen items)
   - hardware (computers, consoles, peripherals, devices, cables)
   - object (misc physical things, tools, household items, folders, vehicles, nature, plants, UI elements)
   - symbol (flags, logos, abstract shapes, signs, text, attribution)

3. **themes**: Tags describing what the icon is about. Use 3-8 tags per icon. Be specific and generous.
   Use existing tags where they fit: """ + ", ".join(KNOWN_TAGS[:100]) + """...
   But also invent new specific tags when needed (e.g., a Scooby-Doo icon should get "scoobydoo", a Matrix icon should get "matrix").
   Tags should be lowercase, no spaces, descriptive. More specific is better than generic.

4. **vibes**: 1-3 mood/aesthetic words. Can be anything — playful, technical, spooky, cozy, elegant, quirky, minimal, retro, cheerful, mysterious, fierce, heroic, etc.

5. **colors**: 1-3 dominant colors (lowercase)

Respond with JSON array, one object per icon in order shown:
[{"file": "filename.png", "description": "...", "category": "...", "themes": ["..."], "vibes": ["..."], "colors": ["..."]}]

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

    # Build set of fully-tagged files (have both tags AND description)
    tagged_set = set()
    needs_retag = set()  # tagged but missing description

    for icon in tags.get("icons", []):
        if icon.get("description"):
            tagged_set.add(icon["file"])
        else:
            needs_retag.add(icon["file"])

    # Also include tagged_files list for backwards compat
    for f in tags.get("tagged_files", []):
        if f not in tagged_set and f not in needs_retag:
            tagged_set.add(f)

    # Remove incomplete entries so they get re-tagged with descriptions
    if needs_retag:
        tags["icons"] = [i for i in tags["icons"] if i["file"] not in needs_retag]
        tags["tagged_files"] = [f for f in tags.get("tagged_files", []) if f not in needs_retag]
        print(f"Re-tagging {len(needs_retag)} icons missing descriptions")

    # Ensure tagged_files is in sync
    tags["tagged_files"] = sorted(list(tagged_set))

    # Find remaining files (untagged + needs retag)
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
