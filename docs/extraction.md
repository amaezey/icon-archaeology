# Icon Extraction Technical Reference

## Source Material

Classic Mac OS icons are stored in resource forks, a secondary data stream unique to HFS/HFS+ filesystems. On modern macOS, these are accessed via the `..namedfork/rsrc` path suffix.

Each icon is a folder containing an `Icon\r` file (with literal carriage return in the filename) that stores the icon data in extended attributes.

## Resource Types

| Type | Size | Description |
|------|------|-------------|
| `icl8` | 1024 bytes | 32×32 8-bit color icon (1 byte/pixel) |
| `ICN#` | 256 bytes | 32×32 1-bit icon (128 bytes) + 1-bit mask (128 bytes) |
| `icl4` | 512 bytes | 32×32 4-bit color icon (not used) |
| `ics8` | 256 bytes | 16×16 8-bit color icon (not used) |

## Mac OS 8-bit System Palette

Sourced from [resource_dasm](https://github.com/fuzziqersoftware/resource_dasm) (MIT licensed):

```
Indices 0-215:   6×6×6 color cube (216 colors)
Indices 216-225: Red ramp (10 shades)
Indices 226-235: Green ramp (10 shades)
Indices 236-245: Blue ramp (10 shades)
Indices 246-255: Gray ramp (10 shades, ending with black)
```

### Color Cube Generation

```python
for r in range(6):
    for g in range(6):
        for b in range(6):
            color = (0xFF - r * 0x33, 0xFF - g * 0x33, 0xFF - b * 0x33)
```

## Mask Extraction

The ICN# resource contains both a 1-bit icon and a 1-bit mask:

```
Bytes 0-127:   1-bit icon (not used for extraction)
Bytes 128-255: 1-bit mask (1 = opaque, 0 = transparent)
```

Each row is 4 bytes (32 bits), MSB first.

## Dependencies

```bash
pip install rsrcfork pillow
```

- **rsrcfork**: Library for reading Mac resource forks
- **Pillow**: Image creation and manipulation

## Usage

```bash
# Opaque extraction (white backgrounds)
python scripts/extract_icons.py ./Media/Icons ./output

# Transparent extraction (using ICN# masks)
python scripts/extract_icons.py ./Media/Icons ./output --transparent
```

## Output Naming

Icons are named `{category}--{name}.png` where:
- `category` is the grandparent folder (collection name)
- `name` is the parent folder (icon name)

Example: `alive--bunny.png` from `Media/Icons/ALIVE/bunny/Icon\r`

## Display in HTML

```html
<img src="icon.png" style="image-rendering: pixelated;">
```

The `pixelated` rendering mode preserves crisp edges when scaling 32×32 icons.

## Notes

- Resource ID -16455 is the standard macOS custom icon resource ID
- Icons without ICN# masks are extracted fully opaque
- The `Icon\r` filename requires special handling in shells: `Icon$'\r'`
