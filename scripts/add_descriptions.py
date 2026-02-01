#!/usr/bin/env python3
"""
Add descriptions to existing tagged icons.

Reads tags.json, finds icons without descriptions, and adds them via Claude vision API.
Progress is saved after each batch.

Usage:
    export ANTHROPIC_API_KEY=your_key
    python add_descriptions.py
"""

import anthropic
import base64
import json
import sys
from pathlib import Path
from time import sleep

ICONS_DIR = Path("/Users/mae/Documents/Inspo space/public/icons/extracted-transparent")
TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/tags.json")

BATCH_SIZE = 10
MODEL = "claude-sonnet-4-20250514"

DESCRIPTION_PROMPT = """Describe each classic Mac OS icon in a brief phrase (3-8 words).

Focus on WHAT the icon depicts, not interpretation. Be specific and literal.

Examples of good descriptions:
- "yellow smiley face with sunglasses"
- "blue folder with red apple logo"
- "steaming cup of coffee"
- "gray computer keyboard"
- "cartoon cat face winking"

For each icon, respond with just the description. Output as JSON array in order shown:
["description 1", "description 2", ...]

Only output the JSON array, no other text."""


def load_image_as_base64(path):
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def load_tags():
    with open(TAGS_FILE) as f:
        return json.load(f)


def save_tags(data):
    tmp = TAGS_FILE.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    tmp.rename(TAGS_FILE)


def describe_batch(client, icon_paths):
    """Get descriptions for a batch of icons."""
    content = []
    filenames = []

    for path in icon_paths:
        filename = path.name
        filenames.append(filename)

        try:
            image_data = load_image_as_base64(path)
            content.append({
                "type": "text",
                "text": f"Icon {len(filenames)}:"
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
        "text": DESCRIPTION_PROMPT
    })

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text.strip()

    # Handle markdown code blocks
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    descriptions = json.loads(response_text)
    return list(zip(filenames, descriptions))


def main():
    print("Icon Description Adder")
    print("=" * 50)

    client = anthropic.Anthropic()
    tags = load_tags()

    # Build lookup from filename to index
    file_to_idx = {icon["file"]: idx for idx, icon in enumerate(tags["icons"])}

    # Find icons without descriptions
    needs_description = [
        icon["file"] for icon in tags["icons"]
        if "description" not in icon or not icon["description"]
    ]

    print(f"Total icons: {len(tags['icons'])}")
    print(f"Need descriptions: {len(needs_description)}")

    if not needs_description:
        print("All icons already have descriptions!")
        return

    total_batches = (len(needs_description) + BATCH_SIZE - 1) // BATCH_SIZE
    batch_num = 0
    added = 0

    for i in range(0, len(needs_description), BATCH_SIZE):
        batch_files = needs_description[i:i + BATCH_SIZE]
        batch_paths = [ICONS_DIR / f for f in batch_files if (ICONS_DIR / f).exists()]
        batch_num += 1

        if not batch_paths:
            continue

        print(f"Batch {batch_num}/{total_batches}: Describing {len(batch_paths)} icons...", end=" ", flush=True)

        try:
            results = describe_batch(client, batch_paths)

            for filename, description in results:
                if filename in file_to_idx:
                    idx = file_to_idx[filename]
                    tags["icons"][idx]["description"] = description
                    added += 1

            save_tags(tags)
            print(f"Done. Progress: {added}/{len(needs_description)}")

            if batch_num < total_batches:
                sleep(0.5)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            continue

        except anthropic.APIError as e:
            print(f"API error: {e}")
            if "rate" in str(e).lower():
                print("Rate limited. Waiting 30s...")
                sleep(30)
            else:
                sleep(5)
            continue

        except KeyboardInterrupt:
            print("\nInterrupted. Progress saved.")
            save_tags(tags)
            sys.exit(0)

    print()
    print(f"Complete! Added {added} descriptions.")


if __name__ == "__main__":
    main()
