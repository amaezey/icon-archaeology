#!/usr/bin/env python3
"""
Semantic tag enrichment using Claude.

Analyzes icon metadata (filename, display_name, collection, path) and adds
missing semantic tags based on world knowledge - franchises, specific sports,
media types, cultural references, etc.
"""

import json
import anthropic
import time
from pathlib import Path

INPUT_FILE = Path(__file__).parent.parent / "public" / "tags.json"
OUTPUT_FILE = Path(__file__).parent.parent / "public" / "tags-semantic.json"

# Tags that Claude should consider adding
SEMANTIC_TAGS = """
FRANCHISES/IP:
- starwars, startrek, matrix, simpsons, peanuts, garfield, disney, pixar
- mario, zelda, pokemon, sonic, finalfantasy
- marvel, dc, batman, superman, spiderman
- harrypotter, lotr, tolkien
- barbie, lego, transformers
- sesamestreet, muppets, drseuss
- sanrio, hellokitty, rilakkuma
- ultraman, godzilla, gundam, evangelion

MEDIA TYPE:
- film, tv, comics, manga, videogame, boardgame
- tokusatsu (Japanese special effects shows like Ultraman)

SPORTS (specific):
- soccer, americanfootball, baseball, basketball, hockey, tennis, golf
- fishing, skiing, skating, swimming, cycling, boxing, wrestling
- olympics, worldcup, nfl, nba, mlb

INTERNET/TECH ERA:
- internet, web, aol, netscape, email, browser
- mac, windows, linux, unix

CULTURAL:
- american, british, french, german, italian, spanish
- chinese, korean, taiwanese
- mexican, brazilian

STYLE/ERA:
- 80s, 90s, y2k, millennium
- artdeco, nouveau, bauhaus, pixel
"""

client = anthropic.Anthropic()

def analyze_batch(icons: list[dict]) -> list[dict]:
    """Send a batch of icons to Claude for semantic analysis."""

    # Format icons for analysis
    icon_texts = []
    for i, icon in enumerate(icons):
        text = f"""[{i}]
file: {icon.get('file', '')}
name: {icon.get('display_name', '')}
collection: {icon.get('collection', '')}
path: {' > '.join(icon.get('path', []))}
current_themes: {', '.join(icon.get('themes', []))}"""
        icon_texts.append(text)

    prompt = f"""Analyze these icon metadata entries and suggest additional semantic tags that are missing.

AVAILABLE TAGS TO ADD:
{SEMANTIC_TAGS}

ICONS TO ANALYZE:
{chr(10).join(icon_texts)}

For each icon, respond with ONLY the index and new tags to ADD (not existing ones).
If no tags should be added, skip that icon entirely.

Format:
[index]: tag1, tag2, tag3

Example:
[0]: simpsons, tv, americanfootball
[3]: matrix, film, scifi
[7]: fishing

Be conservative - only add tags you're confident about based on the metadata."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse response
    results = {}
    for line in response.content[0].text.strip().split('\n'):
        line = line.strip()
        if line.startswith('[') and ']:' in line:
            try:
                idx_str, tags_str = line.split(']:', 1)
                idx = int(idx_str[1:])
                tags = [t.strip().lower() for t in tags_str.split(',') if t.strip()]
                if tags:
                    results[idx] = tags
            except:
                continue

    return results


def main():
    print("Loading tags.json...")
    with open(INPUT_FILE) as f:
        data = json.load(f)

    icons = data['icons']
    print(f"Loaded {len(icons)} icons")

    # Process in batches
    BATCH_SIZE = 30
    total_enriched = 0

    for batch_start in range(0, len(icons), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(icons))
        batch = icons[batch_start:batch_end]

        print(f"\nProcessing {batch_start}-{batch_end}...")

        try:
            results = analyze_batch(batch)

            for local_idx, new_tags in results.items():
                global_idx = batch_start + local_idx
                current_themes = set(icons[global_idx].get('themes', []))
                added = [t for t in new_tags if t not in current_themes]
                if added:
                    icons[global_idx]['themes'] = list(current_themes | set(added))
                    total_enriched += 1
                    print(f"  + {icons[global_idx]['file'][:40]}: {added}")

            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(2)

    print(f"\n\nEnriched {total_enriched} icons")
    print(f"Saving to {OUTPUT_FILE}...")

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print("Done!")


if __name__ == "__main__":
    main()
