# icon-archaeology

## Project Overview

A creative project extracting and showcasing classic Mac OS icons from resource forks.

**Spin-off from:** inspo-space (files remain shared in `../Inspo space/`)

## Directory Structure

```
icon-archaeology/           <- This project (own git repo)
├── scripts/                <- Python extraction tools
├── gallery/                <- Browsable icon gallery
└── docs/                   <- Technical documentation

../Inspo space/             <- Parent project (shared files)
├── Media/Icons/            <- Original icon collections (source)
└── public/icons/           <- Extracted PNGs (output)
    ├── extracted/          <- With white backgrounds
    └── extracted-transparent/  <- With transparency
```

## Key Technical Details

### Resource Fork Format

- Icons stored in `Icon\r` files (carriage return in filename)
- Resource types: `icl8` (32x32 8-bit color), `ICN#` (1-bit mask)
- Mac OS 8-bit palette: 6×6×6 color cube + color ramps

### Dependencies

```bash
pip install rsrcfork pillow
```

## Working Notes

- Icons without ICN# masks extract as fully opaque (white background)
- Use `image-rendering: pixelated` in CSS to preserve pixel art when scaling
- The gallery should support filtering by collection and searching by name
