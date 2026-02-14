#!/usr/bin/env python3
"""
Generate visual descriptions for icons using Claude's vision API.

Describes what each icon LOOKS LIKE — colors, shapes, what it depicts.
Uses the icon's display name and collection as context to help vision
interpret 32x32 pixel art accurately.

Resumable — saves after each batch.
Concurrent — runs 5 API calls in parallel.

Usage:
    ANTHROPIC_API_KEY=... python describe_icons.py [--test N]
"""

import anthropic
import base64
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import sleep, time

ICONS_DIR = Path("/Users/mae/Documents/icon-archaeology/public/icons")
TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")

BATCH_SIZE = 50
WORKERS = 5
MODEL = "claude-sonnet-4-20250514"

PROMPT = """You are describing classic Macintosh icons (32×32 pixel art, 256 colors) for a searchable gallery.

For each icon, write a SHORT, ACCURATE visual description (3-12 words) of what it depicts.

CRITICAL RULES:
- Describe what you SEE in the pixel art — shapes, colors, the subject
- I'm giving you the icon's NAME and COLLECTION as context. USE THEM. A 32×32 icon labeled "Batman" from "Batman Icons" is Batman, not "dark blob"
- Be specific: "cartoon yellow dog face" not "animal", "red apple with green leaf" not "fruit"
- For character icons: mention the character, their expression or pose if visible
- For hardware: identify the device type (laptop, desktop Mac, monitor, keyboard)
- For food: identify the specific food item
- For folders/UI: describe the folder style and any emblems
- For attribution/copyright text icons: just say "attribution text" or "copyright notice"
- DO NOT just repeat the filename — add visual detail the name doesn't capture
- If the icon is too abstract to identify even with the name hint, describe the shapes and colors you see

Respond with a JSON array of description strings, one per icon, in order:
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


def describe_batch(client, icons_batch):
    """Describe a batch of icons using vision + name context."""
    content = []

    for idx, icon in enumerate(icons_batch, 1):
        filename = icon['file']
        name = icon.get('display_name', '') or icon.get('description', '') or filename
        collection = icon.get('collection', '')

        label = f"Icon {idx}: \"{name}\""
        if collection:
            label += f" (from \"{collection}\")"
        content.append({"type": "text", "text": label})

        png_path = ICONS_DIR / filename
        try:
            image_data = load_image_as_base64(png_path)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_data
                }
            })
        except Exception as e:
            content.append({"type": "text", "text": f"[image not available: {e}]"})

    content.append({"type": "text", "text": PROMPT})

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    descriptions = json.loads(response_text)
    return descriptions, response.usage


save_lock = threading.Lock()


def process_batch(client, tags, batch_indices, batch_num, total_batches):
    """Process one batch. Returns (described_count, input_tokens, output_tokens) or None on error."""
    batch_icons = [tags['icons'][idx] for idx in batch_indices]

    try:
        descriptions, usage = describe_batch(client, batch_icons)

        with save_lock:
            for j, desc in enumerate(descriptions):
                if j < len(batch_indices):
                    idx = batch_indices[j]
                    tags['icons'][idx]['description'] = desc

        return len(descriptions), usage.input_tokens, usage.output_tokens

    except json.JSONDecodeError as e:
        print(f"\n  Batch {batch_num}: JSON parse error: {e}")
        return None

    except anthropic.APIError as e:
        print(f"\n  Batch {batch_num}: API error: {e}")
        if "rate" in str(e).lower():
            sleep(30)
        elif "credit" in str(e).lower() or "balance" in str(e).lower():
            print("Credits exhausted!")
            with save_lock:
                save_tags(tags)
            sys.exit(1)
        else:
            sleep(5)
        return None


def main():
    test_mode = None
    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        test_mode = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 10
        print(f"TEST MODE: Processing only {test_mode} icons")

    print("Icon Describer - Vision API (concurrent)")
    print("=" * 50)

    client = anthropic.Anthropic()
    tags = load_tags()

    need_indices = []
    for idx, icon in enumerate(tags['icons']):
        desc = icon.get('description', '')
        display = icon.get('display_name', '')
        if desc and desc != display and len(desc) > 5 and ' ' in desc:
            continue
        need_indices.append(idx)

    print(f"Total icons: {len(tags['icons'])}")
    print(f"Need descriptions: {len(need_indices)}")
    print(f"Batch size: {BATCH_SIZE}, Workers: {WORKERS}")

    if test_mode:
        need_indices = need_indices[:test_mode]

    if not need_indices:
        print("All icons already have descriptions!")
        return

    total_batches = (len(need_indices) + BATCH_SIZE - 1) // BATCH_SIZE
    described = 0
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time()
    save_every = 5  # save after every 5 batches

    # Build all batch index lists
    all_batches = []
    for i in range(0, len(need_indices), BATCH_SIZE):
        all_batches.append(need_indices[i:i + BATCH_SIZE])

    completed_batches = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {}
        for batch_num, batch_indices in enumerate(all_batches, 1):
            future = executor.submit(process_batch, client, tags, batch_indices, batch_num, total_batches)
            futures[future] = batch_num

        for future in as_completed(futures):
            batch_num = futures[future]
            result = future.result()
            completed_batches += 1

            if result:
                count, inp, out = result
                described += count
                total_input_tokens += inp
                total_output_tokens += out

            elapsed = time() - start_time
            rate = described / elapsed if elapsed > 0 else 0
            remaining_icons = len(need_indices) - described
            eta = remaining_icons / rate if rate > 0 else 0

            print(f"\r  {described}/{len(need_indices)} described | "
                  f"{rate:.0f} icons/s | "
                  f"ETA {eta/60:.0f}m | "
                  f"${(total_input_tokens * 3 + total_output_tokens * 15) / 1_000_000:.2f}",
                  end="", flush=True)

            if completed_batches % save_every == 0:
                with save_lock:
                    save_tags(tags)

    # Final save
    save_tags(tags)

    elapsed = time() - start_time
    total_cost = (total_input_tokens * 3 + total_output_tokens * 15) / 1_000_000

    print()
    print()
    print(f"Complete! Described {described} icons in {elapsed:.0f}s.")
    print(f"Tokens: {total_input_tokens} input, {total_output_tokens} output")
    print(f"Total cost: ${total_cost:.2f}")


if __name__ == "__main__":
    main()
