#!/usr/bin/env python3
"""
Extract classic Mac OS icons from resource forks.

Usage:
    python extract_icons.py <icons_dir> <output_dir> [--transparent]

Examples:
    python extract_icons.py ../Media/Icons ./output
    python extract_icons.py ../Media/Icons ./output --transparent
"""
import os
import sys
from pathlib import Path

try:
    from PIL import Image
    import rsrcfork
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install rsrcfork pillow")
    sys.exit(1)

# Mac OS 8-bit system palette from resource_dasm
# https://github.com/fuzziqersoftware/resource_dasm/blob/master/src/ResourceFile.cc
PALETTE = []

# 6x6x6 color cube (indices 0-215)
for r in range(6):
    for g in range(6):
        for b in range(6):
            PALETTE.append((
                0xFF - (r * 0x33),
                0xFF - (g * 0x33),
                0xFF - (b * 0x33)
            ))

# Red ramp (indices 216-225)
for v in [0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA, 0x99, 0x88, 0x77, 0x66]:
    PALETTE.append((v, 0x00, 0x00))

# Green ramp (indices 226-235)
for v in [0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA, 0x99, 0x88, 0x77, 0x66]:
    PALETTE.append((0x00, v, 0x00))

# Blue ramp (indices 236-245)
for v in [0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA, 0x99, 0x88, 0x77, 0x66]:
    PALETTE.append((0x00, 0x00, v))

# Gray ramp (indices 246-255) - ends with black at index 255
for v in [0xEE, 0xDD, 0xCC, 0xBB, 0xAA, 0x99, 0x88, 0x77, 0x66, 0x00]:
    PALETTE.append((v, v, v))


def extract_mask_from_icn(icn_data):
    """
    Extract the 32x32 1-bit mask from ICN# resource.

    ICN# is 256 bytes:
    - First 128 bytes: 1-bit icon
    - Second 128 bytes: 1-bit mask
    """
    if len(icn_data) < 256:
        return None

    mask_data = icn_data[128:256]
    mask = Image.new('L', (32, 32))
    pixels = mask.load()

    for y in range(32):
        for x in range(32):
            byte_idx = y * 4 + (x // 8)
            bit_idx = 7 - (x % 8)
            pixels[x, y] = 255 if mask_data[byte_idx] & (1 << bit_idx) else 0

    return mask


def extract_icl8(icl8_data, mask=None):
    """
    Extract 32x32 8-bit color icon.

    icl8 is 1024 bytes (32x32 pixels, 1 byte per pixel).
    Each byte is an index into the 256-color palette.
    """
    if len(icl8_data) < 1024:
        return None

    if mask:
        img = Image.new('RGBA', (32, 32))
        pixels = img.load()
        mask_pixels = mask.load()

        for y in range(32):
            for x in range(32):
                idx = icl8_data[y * 32 + x]
                r, g, b = PALETTE[idx]
                a = mask_pixels[x, y]
                pixels[x, y] = (r, g, b, a)
    else:
        img = Image.new('RGB', (32, 32))
        pixels = img.load()

        for y in range(32):
            for x in range(32):
                idx = icl8_data[y * 32 + x]
                pixels[x, y] = PALETTE[idx]

    return img


def sanitize_name(name):
    """Convert folder name to safe filename."""
    return ''.join(c if c.isalnum() or c in '-_' else '-' for c in name.lower()).strip('-')


def extract_icons(icons_dir, output_dir, transparent=False):
    """
    Extract all icons from a directory structure.

    Expected structure:
    icons_dir/
      Category1/
        IconName1/
          Icon\r   <- macOS custom icon file with resource fork
        IconName2/
          Icon\r
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted = 0
    no_mask = 0
    errors = 0

    for icon_dir in Path(icons_dir).rglob('*'):
        if not icon_dir.is_dir():
            continue

        icon_file = icon_dir / "Icon\r"
        rsrc_path = str(icon_file) + "/..namedfork/rsrc"

        if not os.path.exists(rsrc_path):
            continue

        try:
            with open(rsrc_path, "rb") as f:
                if f.read(1) == b'':
                    continue
                f.seek(0)
                rf = rsrcfork.ResourceFile(f)

                if b'icl8' not in rf:
                    continue

                # Get mask resources
                icn_masks = {}
                if transparent and b'ICN#' in rf:
                    for res_id in rf[b'ICN#']:
                        try:
                            icn_masks[res_id] = rf[b'ICN#'][res_id].data
                        except Exception:
                            pass

                # Category from grandparent folder, name from parent folder
                category = sanitize_name(icon_dir.parent.name)
                icon_name = sanitize_name(icon_dir.name)

                for res_id in rf[b'icl8']:
                    try:
                        res = rf[b'icl8'][res_id]
                        icl8_data = res.data

                        if len(icl8_data) < 1024:
                            continue

                        mask = None
                        if transparent and res_id in icn_masks:
                            mask = extract_mask_from_icn(icn_masks[res_id])
                        elif transparent:
                            no_mask += 1

                        img = extract_icl8(icl8_data, mask)
                        if img is None:
                            continue

                        filename = f"{category}--{icon_name}.png"
                        img.save(output_dir / filename)
                        extracted += 1

                    except Exception as e:
                        errors += 1
                        continue

        except Exception as e:
            errors += 1
            continue

    print(f"Extracted: {extracted} icons")
    if transparent:
        print(f"No mask:   {no_mask} icons (extracted opaque)")
    if errors:
        print(f"Errors:    {errors}")

    return extracted


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract classic Mac OS icons from resource forks"
    )
    parser.add_argument("icons_dir", help="Directory containing icon folders")
    parser.add_argument("output_dir", help="Directory to save extracted PNGs")
    parser.add_argument(
        "--transparent", "-t",
        action="store_true",
        help="Extract with transparency using ICN# masks"
    )

    args = parser.parse_args()

    if not os.path.isdir(args.icons_dir):
        print(f"Error: {args.icons_dir} is not a directory")
        sys.exit(1)

    extract_icons(args.icons_dir, args.output_dir, args.transparent)


if __name__ == "__main__":
    main()
