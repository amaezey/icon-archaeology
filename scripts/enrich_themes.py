#!/usr/bin/env python3
"""
Enrich icon themes using text-only API calls (no vision).

Uses description, filename, collection, and existing tags to generate
richer themes. Processes 100 icons per batch for efficiency.

Resumable — saves after each batch.

Usage:
    ANTHROPIC_API_KEY=... python enrich_themes.py
"""

import anthropic
import json
import sys
from pathlib import Path
from time import sleep

TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")
BATCH_SIZE = 100
MODEL = "claude-sonnet-4-20250514"

KNOWN_TAGS = (
    "3d,60s,90s,abstract,adventure,advertising,aeonflux,alien,american,ancient,"
    "animal,animaniacs,animation,anime,aol,apollo,apple,aqua,aquarium,archie,art,"
    "astronomy,audio,australia,autumn,aviation,bakery,batman,beatles,bento,blizzard,"
    "bloomcounty,book,botanical,bread,breakfast,british,burger,cafe,cake,calvinandhobbes,"
    "candy,cartoon,cat,celtic,cereal,charliebrown,chat,cheese,children,chinese,christmas,"
    "cinema,citrus,classic,claymation,cleaning,climbing,clone,coatofarms,coffee,cold,"
    "comics,communication,computer,cooking,copland,cowboy,creature,creative,cultural,"
    "curry,cute,czech,dairy,dc,deli,design,dessert,diablo,dinner,disney,donuts,dreamcast,"
    "drink,drseuss,euro2000,european,eworld,fall,fantasy,fashion,fastfood,february,"
    "fighting,film,fish,fishing,flintstones,flowers,folder,food,football,fox,fruit,"
    "fujiya,furby,futurama,gaming,garfield,geometric,glossy,graffiti,guitar,haagendazs,"
    "halloween,handdrawn,handheld,hannabarbera,hardware,healthy,heraldry,hiking,holiday,"
    "homm,horror,household,humor,ibook,icecream,illustration,imac,indigenous,industrial,"
    "insignia,instrument,interface,internet,irish,italian,japanese,jleague,kaiju,katsu,"
    "kids,kitchen,korean,laptop,looneytunes,love,lucasfilm,lure,m68k,mac,macos,manga,"
    "marvel,matrix,meal,mecha,medieval,military,minimal,monster,morning,mortalkombat,"
    "motorola,mountain,mtv,muppets,music,mystery,nasa,nature,newton,newyear,nickelodeon,"
    "nintendo,noodles,nostalgia,october,office,okashi,olympics,online,osechi,osx,outdoor,"
    "palm,pbs,pda,peanuts,pet,pie,pizza,planets,plant,pokemon,popeye,portrait,powerpc,"
    "premierleague,produce,quiet,racing,ramen,renandstimpy,retro,robot,rockyandbullwinkle,"
    "rogerrabbit,rpg,science,scifi,scoobydoo,season,sega,seriea,sesamestreet,simpsons,"
    "sketch,smurfs,snacks,snow,soccer,sonic,sony,southamerican,southpark,space,speedracer,"
    "spooky,sports,spring,startrek,starwars,stationery,storage,stpatricks,strategy,"
    "streetfood,studio,summer,superhero,sushi,sweets,sydney2000,symbol,tea,technical,"
    "thunderbirds,tinytoons,tmnt,tokusatsu,tools,toy,traditional,tv,ui,ultraman,urban,"
    "valentine,valentines,vegetables,vegetarian,vehicle,video,videogame,vintage,wagashi,"
    "wallaceandgromit,warehouse,warnerbros,wb,western,winter,writing,yosemite"
)

PROMPT = """You are tagging classic Mac OS icons for a gallery. Each icon below has a filename, description, collection, and existing tags. Your job is to ENRICH the tags — add specific, relevant tags that are missing.

EXISTING TAGS in the gallery (use these where they fit, but also invent new specific ones):
""" + KNOWN_TAGS + """

RULES:
- Return 4-10 tags per icon (including any good existing ones)
- Be SPECIFIC: "simpsons" not just "cartoon", "sushi" not just "food", "imac" not just "hardware"
- Use the icon's collection name as a clue (e.g., collection "Ren&Stimpy icons" → tag "renandstimpy")
- Invent new tags when needed: franchise names, specific subjects, cultural references
- Tags are lowercase, no spaces (use camelCase or concatenation: "southpark", "startrek")
- Keep existing tags that are correct, drop ones that are wrong
- Every icon should have at least one mood/vibe tag (retro, cute, playful, spooky, technical, etc.)

For each icon, respond with JUST the enriched tags array.

ICONS:
"""


def load_tags():
    with open(TAGS_FILE) as f:
        return json.load(f)


def save_tags(data):
    tmp = TAGS_FILE.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    tmp.rename(TAGS_FILE)


def format_icon_for_prompt(icon, idx):
    """Format one icon's metadata for the prompt."""
    return (
        f"{idx}. file={icon['file']} | "
        f"desc=\"{icon.get('description', '?')}\" | "
        f"collection=\"{icon.get('collection', '?')}\" | "
        f"category={icon.get('category', '?')} | "
        f"existing=[{','.join(icon.get('themes', []))}]"
    )


def enrich_batch(client, icons_batch):
    """Enrich themes for a batch of icons using text-only API."""
    prompt_lines = []
    for idx, icon in enumerate(icons_batch, 1):
        prompt_lines.append(format_icon_for_prompt(icon, idx))

    full_prompt = PROMPT + "\n".join(prompt_lines) + """

Respond with a JSON array of arrays — one inner array of tag strings per icon, in order:
[["tag1","tag2","tag3"], ["tag1","tag2"], ...]

Only output the JSON array, no other text."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": full_prompt}]
    )

    response_text = response.content[0].text.strip()

    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    return json.loads(response_text)


def main():
    print("Theme Enricher - Text-only API")
    print("=" * 50)

    client = anthropic.Anthropic()
    tags = load_tags()

    # Find icons with thin themes (<=5 tags)
    thin_indices = []
    for idx, icon in enumerate(tags['icons']):
        if len(icon.get('themes', [])) <= 5:
            thin_indices.append(idx)

    print(f"Total icons: {len(tags['icons'])}")
    print(f"Need enrichment (<=5 themes): {len(thin_indices)}")

    if not thin_indices:
        print("All icons already have rich themes!")
        return

    total_batches = (len(thin_indices) + BATCH_SIZE - 1) // BATCH_SIZE
    batch_num = 0
    enriched = 0

    for i in range(0, len(thin_indices), BATCH_SIZE):
        batch_indices = thin_indices[i:i + BATCH_SIZE]
        batch_icons = [tags['icons'][idx] for idx in batch_indices]
        batch_num += 1

        print(f"Batch {batch_num}/{total_batches}: Enriching {len(batch_icons)} icons...", end=" ", flush=True)

        try:
            results = enrich_batch(client, batch_icons)

            for j, new_themes in enumerate(results):
                if j < len(batch_indices):
                    idx = batch_indices[j]
                    # Merge: keep existing, add new
                    existing = set(tags['icons'][idx].get('themes', []))
                    new_set = set(t.lower().strip() for t in new_themes if t)
                    merged = sorted(existing | new_set)
                    tags['icons'][idx]['themes'] = merged

                    # Also update vibes from themes
                    vibe_words = {'playful', 'technical', 'spooky', 'cozy', 'elegant',
                                  'quirky', 'minimal', 'retro', 'cute', 'cheerful',
                                  'festive', 'mystical', 'heroic', 'fierce', 'dramatic'}
                    icon_vibes = [t for t in merged if t in vibe_words]
                    if icon_vibes:
                        tags['icons'][idx]['vibes'] = icon_vibes

                    enriched += 1

            save_tags(tags)
            print(f"Done. Progress: {enriched}/{len(thin_indices)}")

            if batch_num < total_batches:
                sleep(0.3)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            continue

        except anthropic.APIError as e:
            print(f"API error: {e}")
            if "rate" in str(e).lower():
                print("Rate limited. Waiting 30s...")
                sleep(30)
            elif "credit" in str(e).lower() or "balance" in str(e).lower():
                print("Credits exhausted. Saving and exiting.")
                save_tags(tags)
                sys.exit(1)
            else:
                sleep(5)
            continue

        except KeyboardInterrupt:
            print("\nInterrupted. Progress saved.")
            save_tags(tags)
            sys.exit(0)

    print()
    print(f"Complete! Enriched {enriched}/{len(thin_indices)} icons.")


if __name__ == "__main__":
    main()
