#!/usr/bin/env python3
"""
Extract classic Mac OS icons from mixed source formats.

This script handles:
1. Structured folders with Icon\r files (e.g., fillerbunny ƒ/Vomit/Icon\r)
2. Flat collections where files themselves have resource forks (e.g., ALIEN Icons/*)
3. Collections using both formats simultaneously (e.g., Matrix icons)
4. icns container resources (wrapping icl8/ICN#/l8mk data)

The icons are extracted as 32x32 PNG files with transparency (when mask data exists).

Usage:
    python extract_batch.py /path/to/source /path/to/output

Examples:
    # Extract from a folder of icon collections
    python extract_batch.py ~/Downloads/icons ./staging

    # Extract directly to the public icons folder
    python extract_batch.py ~/Downloads/icons ../public/icons

Output naming:
    Files are named "{collection}--{icon_name}.png"
    Duplicates get numeric suffixes: "{collection}--{icon_name}-1.png"

Requirements:
    pip install rsrcfork pillow
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

# Mac OS 8-bit system palette (256 colors)
# This is the standard palette used by icl8 resources
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

# Gray ramp (indices 246-255)
for v in [0xEE, 0xDD, 0xCC, 0xBB, 0xAA, 0x99, 0x88, 0x77, 0x66, 0x00]:
    PALETTE.append((v, v, v))


def extract_mask_from_icn(icn_data):
    """Extract 32x32 1-bit mask from ICN# resource.

    The ICN# resource contains both the icon bitmap (first 128 bytes) and
    the mask (second 128 bytes). We only need the mask for transparency.
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
    """Extract 32x32 8-bit color icon.

    Args:
        icl8_data: Raw bytes from icl8 resource (1024 bytes for 32x32)
        mask: Optional PIL Image mask for transparency

    Returns:
        PIL Image (RGBA if mask provided, RGB otherwise)
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
    """Convert to safe filename, preserving readability."""
    # Remove problematic characters but keep meaningful ones
    safe = ''.join(c if c.isalnum() or c in '-_ ' else '-' for c in name)
    # Collapse multiple dashes/spaces
    while '--' in safe:
        safe = safe.replace('--', '-')
    while '  ' in safe:
        safe = safe.replace('  ', ' ')
    return safe.strip('- ')


def parse_icns_container(icns_data):
    """Parse an icns container and return a dict of element type -> data.

    The icns format is a simple container:
    - 4 bytes: 'icns' magic
    - 4 bytes: total length (big-endian)
    - Repeated elements: 4-byte type + 4-byte length + data
    """
    import struct
    elements = {}
    pos = 0

    if len(icns_data) >= 8 and icns_data[:4] == b'icns':
        pos = 8

    while pos < len(icns_data) - 8:
        etype = icns_data[pos:pos+4]
        elen = struct.unpack('>I', icns_data[pos+4:pos+8])[0]
        if elen < 8 or elen > len(icns_data) - pos:
            break
        elements[etype] = icns_data[pos+8:pos+elen]
        pos += elen

    return elements


def extract_from_icns(icns_data):
    """Extract a 32x32 icon from an icns container.

    Looks for icl8 (8-bit color) + ICN# or l8mk (mask) inside the container.
    Prefers l8mk (8-bit alpha) over ICN# (1-bit mask) for smoother edges.
    """
    elements = parse_icns_container(icns_data)

    icl8_data = elements.get(b'icl8')
    if not icl8_data or len(icl8_data) < 1024:
        return None

    # Prefer l8mk (8-bit alpha mask) over ICN# (1-bit mask)
    mask = None
    l8mk_data = elements.get(b'l8mk')
    if l8mk_data and len(l8mk_data) >= 1024:
        mask = Image.new('L', (32, 32))
        pixels = mask.load()
        for y in range(32):
            for x in range(32):
                pixels[x, y] = l8mk_data[y * 32 + x]
    else:
        icn_data = elements.get(b'ICN#')
        if icn_data:
            mask = extract_mask_from_icn(icn_data)

    return extract_icl8(icl8_data, mask)


def extract_from_rsrc(rsrc_path, collection, icon_name):
    """Extract icon from a resource fork path.

    Handles both direct icl8 resources and icns containers.

    Args:
        rsrc_path: Path to the resource fork (usually file/..namedfork/rsrc)
        collection: Collection name for logging
        icon_name: Icon name for logging

    Returns:
        PIL Image or None if extraction failed
    """
    try:
        with open(rsrc_path, "rb") as f:
            if f.read(1) == b'':
                return None
            f.seek(0)
            rf = rsrcfork.ResourceFile(f)

            # Try direct icl8 resources first (most common)
            if b'icl8' in rf:
                icn_masks = {}
                l8mk_masks = {}
                if b'ICN#' in rf:
                    for res_id in rf[b'ICN#']:
                        try:
                            icn_masks[res_id] = rf[b'ICN#'][res_id].data
                        except Exception:
                            pass

                for res_id in rf[b'icl8']:
                    try:
                        res = rf[b'icl8'][res_id]
                        icl8_data = res.data

                        if len(icl8_data) < 1024:
                            continue

                        mask = None
                        if res_id in icn_masks:
                            mask = extract_mask_from_icn(icn_masks[res_id])

                        img = extract_icl8(icl8_data, mask)
                        if img:
                            return img
                    except Exception:
                        continue

            # Try icns container resources (wraps icl8/ICN#/l8mk)
            if b'icns' in rf:
                for res_id in rf[b'icns']:
                    try:
                        icns_data = rf[b'icns'][res_id].data
                        img = extract_from_icns(icns_data)
                        if img:
                            return img
                    except Exception:
                        continue

    except Exception:
        pass

    return None


def extract_all(source_dir, output_dir):
    """Extract icons from all collections in source directory.

    Args:
        source_dir: Directory containing icon collections
        output_dir: Directory to save extracted PNGs

    Returns:
        Number of icons extracted
    """
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted = 0
    skipped = 0

    print(f"Scanning {source_dir}...")

    # Process each top-level collection
    for collection_dir in sorted(source_dir.iterdir()):
        if not collection_dir.is_dir():
            continue
        if collection_dir.name.startswith('.'):
            continue

        collection_name = sanitize_name(collection_dir.name)
        print(f"\n=== {collection_dir.name} ===")
        collection_count = 0

        # Track which files we've already processed (avoid extracting Icon\r
        # files twice — once as structured, once as flat)
        processed_paths = set()

        # Pass 1: Extract from Icon\r files (structured format)
        for icon_file in collection_dir.rglob('Icon\r'):
            processed_paths.add(icon_file.resolve())

            rsrc_path = str(icon_file) + "/..namedfork/rsrc"
            if not os.path.exists(rsrc_path):
                continue

            # Get icon name from parent folder
            icon_name = sanitize_name(icon_file.parent.name)
            if not icon_name or icon_name.lower() in ['icon', 'icons']:
                icon_name = collection_name

            filename = f"{collection_name}--{icon_name}.png"
            dest = output_dir / filename

            # Handle duplicates with numeric suffix
            if dest.exists():
                i = 1
                while dest.exists():
                    filename = f"{collection_name}--{icon_name}-{i}.png"
                    dest = output_dir / filename
                    i += 1

            img = extract_from_rsrc(rsrc_path, collection_name, icon_name)
            if img:
                img.save(dest)
                extracted += 1
                collection_count += 1
            else:
                skipped += 1

        # Pass 2: Extract from individual files with resource forks
        # Recurses into subfolders (e.g., Matrix icons/Morpheus/Neo)
        for item in collection_dir.rglob('*'):
            if item.is_dir():
                continue
            if item.name.startswith('.'):
                continue
            if item.resolve() in processed_paths:
                continue

            rsrc_path = str(item) + "/..namedfork/rsrc"
            if not os.path.exists(rsrc_path):
                continue

            icon_name = sanitize_name(item.name)
            if not icon_name:
                icon_name = "unnamed"

            filename = f"{collection_name}--{icon_name}.png"
            dest = output_dir / filename

            # Handle duplicates with numeric suffix
            if dest.exists():
                i = 1
                while dest.exists():
                    filename = f"{collection_name}--{icon_name}-{i}.png"
                    dest = output_dir / filename
                    i += 1

            img = extract_from_rsrc(rsrc_path, collection_name, icon_name)
            if img:
                img.save(dest)
                extracted += 1
                collection_count += 1
            else:
                skipped += 1

        if collection_count > 0:
            print(f"  Extracted: {collection_count}")

    print(f"\n{'='*50}")
    print(f"Total extracted: {extracted}")
    print(f"Skipped: {skipped}")
    print(f"Output: {output_dir}")

    return extracted


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Extract classic Mac OS icons from resource forks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/Downloads/icons ./staging
  %(prog)s /Volumes/Archive/MacIcons ../public/icons
        """
    )
    parser.add_argument("source_dir", help="Directory containing icon collections")
    parser.add_argument("output_dir", help="Directory to save extracted PNGs")

    args = parser.parse_args()

    if not os.path.isdir(args.source_dir):
        print(f"Error: {args.source_dir} is not a directory")
        sys.exit(1)

    extract_all(args.source_dir, args.output_dir)


if __name__ == "__main__":
    main()
