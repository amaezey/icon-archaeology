# icon-archaeology

Excavating and preserving classic Mac OS icons from resource forks.

## What's Here

This project extracts icons from classic Mac OS icon collections stored with macOS resource forks. Each original icon is a folder containing an `Icon\r` file that stores icon data in extended attributes using the Mac OS 8-bit system palette.

### Source Collections

Located in `../Inspo space/Media/Icons/`:

| Collection | Icons | Description |
|------------|-------|-------------|
| Icon Collection | 729 | Large mixed collection |
| interfacials | 59 | Interface elements |
| geometria_tech | 54 | Technical/geometric icons |
| retroish | 41 | Retro-styled icons |
| ALIVE | 30 | Character/creature icons |
| huh | 29 | Miscellaneous |
| edibles | 27 | Food icons |
| junk drawer | 22 | Odds and ends |
| creativejuices | 12 | Creative tools |

### Extracted Icons

Located in `../Inspo space/public/icons/`:

- `extracted/` - ~6,000 icons with white backgrounds
- `extracted-transparent/` - ~15,000 icons with transparency (using ICN# masks)

## Extraction

See [docs/extraction.md](docs/extraction.md) for the technical details and Python scripts.

### Quick Start

```bash
pip install rsrcfork pillow
python scripts/extract_icons.py <source_dir> <output_dir>
```

## Gallery

Open `gallery/index.html` to browse all extracted icons.

## Related

This project is a spin-off from [inspo-space](../Inspo%20space/), which uses these icons as design inspiration.

## License

The extraction scripts are MIT licensed. The icons themselves are vintage Mac OS resources - treat them as historical artifacts for personal/educational use.
