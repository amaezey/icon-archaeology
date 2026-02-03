# icon-archaeology

## Project Overview

A creative project extracting and showcasing classic Mac OS icons from resource forks.

## Directory Structure

```
icon-archaeology/
├── sources/                <- Original icon collections (resource forks)
│   ├── ALIVE/
│   ├── creativejuices/
│   ├── edibles/
│   ├── geometria_tech/
│   ├── huh/
│   ├── Icon Collection/
│   ├── Icon Collection 1/
│   ├── interfacials/
│   ├── junk drawer/
│   └── retroish/
├── public/
│   └── icons/              <- Extracted PNGs (transparent)
├── scripts/                <- Python extraction tools
├── gallery/                <- Browsable icon gallery
└── docs/                   <- Technical documentation
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
