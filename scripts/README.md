# Icon Archaeology Scripts

Tools for extracting, deduplicating, and enriching classic Mac OS icons.

## Requirements

```bash
pip install rsrcfork pillow imagehash
```

For API-powered enrichment (retag_all.py, describe_icons.py):
```bash
pip install anthropic
```

## Workflow

### Adding New Icons (Steps 1–4)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. EXTRACT                                                     │
│     extract_batch.py ~/Downloads/icons ./staging                │
│     → Converts resource forks to PNG files                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. CHECK DUPLICATES                                            │
│     check_duplicates.py ./staging --output truly_new.txt        │
│     → Reports duplicates, saves list of new icons               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. ADD TO ARCHIVE                                              │
│     add_icons_basic.py truly_new.txt                            │
│     → Copies icons to public/icons, creates tags.json entries   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. ENRICH METADATA                                             │
│     enrich_from_metadata.py                                     │
│     → Adds themes/vibes based on collection names               │
│     cp public/tags-enriched.json public/tags.json               │
└─────────────────────────────────────────────────────────────────┘
```

### Post-Processing (optional, needs API key)

These use the Anthropic API and cost money. Run only when needed.

```bash
# Text-only enrichment: validates/adds themes, vibes, categories
ANTHROPIC_API_KEY=$(cat ~/.anthropic_key) python scripts/retag_all.py

# Vision descriptions: generates "what it looks like" text
ANTHROPIC_API_KEY=$(cat ~/.anthropic_key) python scripts/describe_icons.py
```

Both are resumable (save progress after each batch) and concurrent (5 workers).

### Example Session

```bash
cd /Users/mae/Documents/icon-archaeology

# Extract icons from resource forks
python scripts/extract_batch.py ~/Downloads/icons ./staging

# Check what's actually new
python scripts/check_duplicates.py ./staging --output truly_new.txt

# Add new icons to the archive
python scripts/add_icons_basic.py truly_new.txt

# Enrich with themes based on collection names
python scripts/enrich_from_metadata.py
cp public/tags-enriched.json public/tags.json

# Clean up
rm -rf ./staging truly_new.txt
```

## Scripts Reference

### extract_batch.py

Extracts classic Mac OS icons from resource forks.

Handles three source formats:
- **Structured**: Folders with `Icon\r` files (e.g., `collection ƒ/IconName/Icon\r`)
- **Flat**: Files with resource forks directly (e.g., `collection/file`)
- **icns containers**: Files wrapping multiple resource types in a single container

```bash
python extract_batch.py <source_dir> <output_dir>
```

Output files are named `{collection}--{icon_name}.png`. For nested collections,
the hierarchy is preserved: `{collection}--{sub}--{name}.png`.

### check_duplicates.py

Compares icons against the existing archive using perceptual hashing.

```bash
python check_duplicates.py <new_icons_dir> [--output file.txt]
```

### add_icons_basic.py

Adds icons to the archive with basic metadata.

```bash
python add_icons_basic.py <icons_list.txt>
```

Creates entries in `tags.json` with:
- `display_name` derived from filename
- `collection` extracted from filename
- `category: "object"` (default, refined later)
- `vibes: ["retro"]` (default)

### enrich_from_metadata.py

Adds themes and vibes based on collection names and patterns.

```bash
python enrich_from_metadata.py
```

Reads `public/tags.json`, outputs `public/tags-enriched.json`.
Edit `COLLECTION_THEMES` and `COLLECTION_VIBES` dicts in the script to add
patterns for new collections.

### retag_all.py

Text-only API enrichment. For each icon, validates existing themes and adds
missing ones based on display name, description, and collection context.

```bash
ANTHROPIC_API_KEY=... python retag_all.py [--test N] [--resume]
```

### describe_icons.py

Vision-based descriptions. Generates "what it looks like" text for each icon,
using the display name and collection as context to help interpret 32x32 pixel art.

```bash
ANTHROPIC_API_KEY=... python describe_icons.py [--test N]
```

### add_display_names.py

Backfills display names by matching extracted filenames back to the original
source directories.

```bash
python add_display_names.py
```

### deduplicate.py

Groups identical/near-identical icons by perceptual hash and merges metadata,
keeping the best-named version.

```bash
python deduplicate.py
```

## Technical Notes

### Mac OS 8-bit Palette

Icons use the classic Mac OS 8-bit system palette:
- Indices 0–215: 6x6x6 colour cube
- Indices 216–225: Red ramp
- Indices 226–235: Green ramp
- Indices 236–245: Blue ramp
- Indices 246–255: Grey ramp

### Resource Types

**Standalone resources:**
- `icl8`: 32x32 8-bit colour icon (1024 bytes)
- `ICN#`: 32x32 1-bit icon + mask (256 bytes total, mask in second half)

**icns container resources:**
- `icl8` / `ICN#`: Same as above, but wrapped inside an icns container
- `l8mk`: 8-bit alpha mask (1024 bytes) — smoother transparency than ICN#
- `il32`: 32-bit RGB data (variable size, may be compressed)

The mask from `ICN#` (or `l8mk` when available) provides transparency.
Icons without any mask extract as fully opaque with white background.

### Deduplication

Uses perceptual hashing (average hash, 16x16) to detect visually identical
icons even if they have different filenames or slight compression differences.

### tags.json Schema

Each icon entry has:
- `display_name`: Human-readable name from the source collection
- `collection`: Source collection name
- `category`: One of `character`, `food`, `hardware`, `object`, `symbol`
- `themes`: Array of topic tags (e.g., `["simpsons", "cartoon", "tv"]`)
- `vibes`: Array of aesthetic tags (e.g., `["retro", "playful", "colorful"]`)
- `description` (optional): What the icon visually depicts
