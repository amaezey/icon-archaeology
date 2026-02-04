# Icon Archaeology Scripts

Tools for extracting, deduplicating, and enriching classic Mac OS icons.

## Requirements

```bash
pip install rsrcfork pillow imagehash
```

## Workflow

### Adding New Icons

The typical workflow for processing a batch of new icons:

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

### Example Session

```bash
# Got a folder of classic Mac icon collections
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

# Clean up staging folder
rm -rf ./staging truly_new.txt
```

## Scripts Reference

### extract_batch.py

Extracts classic Mac OS icons from resource forks.

Handles two source formats:
- **Structured**: Folders with `Icon\r` files (e.g., `collection ƒ/IconName/Icon\r`)
- **Flat**: Files with resource forks directly (e.g., `collection/file`)

```bash
python extract_batch.py <source_dir> <output_dir>

# Examples
python extract_batch.py ~/Downloads/icons ./staging
python extract_batch.py /Volumes/Archive/MacIcons ../public/icons
```

Output files are named `{collection}--{icon_name}.png`.

### check_duplicates.py

Compares icons against the existing archive using perceptual hashing.

```bash
python check_duplicates.py <new_icons_dir> [--output file.txt]

# Just see report
python check_duplicates.py ./staging

# Save list of new icons for next step
python check_duplicates.py ./staging --output truly_new.txt
```

### add_icons_basic.py

Adds icons to the archive with basic metadata.

```bash
python add_icons_basic.py <icons_list.txt>

# Using output from check_duplicates.py
python add_icons_basic.py truly_new.txt
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

Reads from `public/tags.json`, outputs to `public/tags-enriched.json`.

To apply changes:
```bash
cp public/tags-enriched.json public/tags.json
```

Edit `COLLECTION_THEMES` and `COLLECTION_VIBES` dicts in the script to add
patterns for new collections.

## Technical Notes

### Mac OS 8-bit Palette

Icons use the classic Mac OS 8-bit system palette:
- Indices 0-215: 6×6×6 color cube
- Indices 216-225: Red ramp
- Indices 226-235: Green ramp
- Indices 236-245: Blue ramp
- Indices 246-255: Gray ramp

### Resource Types

- `icl8`: 32×32 8-bit color icon (1024 bytes)
- `ICN#`: 32×32 1-bit icon + mask (256 bytes total, mask in second half)

The mask from `ICN#` is used for transparency when extracting `icl8` icons.

### Deduplication

Uses perceptual hashing (average hash, 16×16) to detect visually identical
icons even if they have different filenames or slight compression differences.
