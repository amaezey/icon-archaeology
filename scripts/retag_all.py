#!/usr/bin/env python3
"""
Validate and enrich themes for ALL icons using text-only API.

For each icon, the model sees the display name, description, collection,
category, and existing themes. It validates each existing theme (keeping
correct ones, dropping wrong ones) and adds missing ones.

Concurrent (5 workers), resumable (saves every 5 batches).

Usage:
    ANTHROPIC_API_KEY=... python retag_all.py [--test N] [--resume]
"""

import anthropic
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import sleep, time

TAGS_FILE = Path("/Users/mae/Documents/icon-archaeology/public/tags.json")
BATCH_SIZE = 100
WORKERS = 5
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

PROMPT = """You are re-tagging classic Mac OS icons for a gallery. Each icon below has metadata and EXISTING themes. Your job is to VALIDATE and ENRICH the themes.

EXISTING TAGS in the gallery (use these where they fit, but also invent new specific ones):
""" + KNOWN_TAGS + """

RULES:
1. VALIDATE each existing theme against the icon's name, description, and collection:
   - KEEP themes that are correct (e.g. "japanese" on a sushi icon — keep it)
   - DROP themes that are wrong (e.g. "boot" on a test tube, "christmas" on a science icon — drop them)
   - When in doubt, keep the theme

2. ADD missing themes:
   - Franchise/IP names: "simpsons", "batman", "pokemon", "starwars", etc.
   - Visual attributes: "pixel", "handdrawn", "3d", "glossy", etc.
   - Subject specifics: "sushi" not just "food", "imac" not just "hardware"
   - Cultural context: "japanese", "american", "european", etc.

3. Every icon MUST have at least one mood/vibe tag:
   retro, cute, playful, spooky, technical, cozy, elegant, quirky, minimal,
   cheerful, festive, mystical, heroic, fierce, dramatic, nostalgic, whimsical, silly

4. Return 4-10 tags per icon (the validated+enriched result)
5. Tags: lowercase, no spaces (concatenate words: "southpark", "startrek")
6. Use the collection name as a clue for franchise/series tags

For each icon, respond with the FINAL tag list (not a diff — the complete set of tags to use).

ICONS:
"""


PROGRESS_FILE = TAGS_FILE.with_name('retag_progress.json')

VIBE_WORDS = {
    'playful', 'technical', 'spooky', 'cozy', 'elegant',
    'quirky', 'minimal', 'retro', 'cute', 'cheerful',
    'festive', 'mystical', 'heroic', 'fierce', 'dramatic',
    'nostalgic', 'whimsical', 'silly', 'eerie', 'warm',
    'cool', 'bold', 'clean', 'vintage', 'modern',
    'dark', 'bright', 'soft', 'gritty', 'sleek'
}


def load_tags():
    with open(TAGS_FILE) as f:
        return json.load(f)


def save_tags(data):
    tmp = TAGS_FILE.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    tmp.rename(TAGS_FILE)


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed_batches": set()}


def save_progress(progress):
    serializable = {
        "completed_batches": sorted(progress["completed_batches"])
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(serializable, f)


def format_icon_for_prompt(icon, idx):
    """Format one icon's metadata for the prompt."""
    name = icon.get('display_name', '') or icon.get('file', '').split('--')[0]
    desc = icon.get('description', '?')
    collection = icon.get('collection', '?')
    category = icon.get('category', '?')
    existing = icon.get('themes', [])
    return (
        f"{idx}. name=\"{name}\" | "
        f"desc=\"{desc}\" | "
        f"collection=\"{collection}\" | "
        f"category={category} | "
        f"existing=[{','.join(existing)}]"
    )


def retag_batch(client, icons_batch):
    """Validate and enrich themes for a batch of icons using text-only API."""
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

    return json.loads(response_text), response.usage


save_lock = threading.Lock()


def process_batch(client, tags, batch_indices, batch_num, total_batches):
    """Process one batch. Returns (count, input_tokens, output_tokens) or None."""
    batch_icons = [tags['icons'][idx] for idx in batch_indices]

    try:
        results, usage = retag_batch(client, batch_icons)

        with save_lock:
            for j, new_themes in enumerate(results):
                if j < len(batch_indices):
                    idx = batch_indices[j]
                    # Replace themes with validated+enriched result
                    cleaned = sorted(set(
                        t.lower().strip().replace(' ', '')
                        for t in new_themes if t and isinstance(t, str)
                    ))
                    tags['icons'][idx]['themes'] = cleaned

                    # Update vibes from mood-type tags
                    icon_vibes = [t for t in cleaned if t in VIBE_WORDS]
                    if icon_vibes:
                        tags['icons'][idx]['vibes'] = icon_vibes
                    elif 'vibes' in tags['icons'][idx]:
                        # Keep existing vibes if model didn't return any vibe tags
                        pass

        return len(results), usage.input_tokens, usage.output_tokens

    except json.JSONDecodeError as e:
        print(f"\n  Batch {batch_num}: JSON parse error: {e}")
        return None

    except anthropic.APIError as e:
        error_str = str(e).lower()
        print(f"\n  Batch {batch_num}: API error: {e}")
        if "rate" in error_str:
            print("  Rate limited. Waiting 30s...")
            sleep(30)
        elif "credit" in error_str or "balance" in error_str:
            print("  Credits exhausted! Saving and exiting.")
            with save_lock:
                save_tags(tags)
            sys.exit(1)
        elif "overloaded" in error_str:
            print("  API overloaded. Waiting 10s...")
            sleep(10)
        else:
            sleep(5)
        return None


# ─── Keyword safety net (post-enrichment) ───

KEYWORD_RULES = {
    # Franchise detection from collection and display names
    "simpsons": {
        "patterns": ["simpsons", "simpson", "bart", "homer", "marge", "krusty",
                      "flanders", "burns", "smithers", "milhouse", "nelson",
                      "wiggum", "apu", "moe", "barney"],
        "tags": ["simpsons", "cartoon", "tv"]
    },
    "pokemon": {
        "patterns": ["pokemon", "pikachu", "bulbasaur", "charmander", "squirtle",
                      "mewtwo", "eevee", "jigglypuff", "snorlax", "pokeball",
                      "ivysaur", "venusaur", "charmeleon", "charizard", "wartortle",
                      "blastoise", "caterpie", "metapod", "butterfree", "weedle",
                      "kakuna", "beedrill", "pidgey", "rattata", "nidoran",
                      "raichu", "sandshrew"],
        "tags": ["pokemon", "nintendo", "gaming", "anime"]
    },
    "starwars": {
        "patterns": ["star wars", "starwars", "darth vader", "yoda", "luke skywalker",
                      "jedi", "lightsaber", "r2d2", "c3po", "chewbacca", "han solo",
                      "death star", "stormtrooper", "boba fett", "millennium falcon"],
        "tags": ["starwars", "scifi", "lucasfilm"]
    },
    "startrek": {
        "patterns": ["star trek", "startrek", "enterprise", "spock", "kirk",
                      "picard", "klingon", "starfleet", "vulcan", "federation"],
        "tags": ["startrek", "scifi", "tv"]
    },
    "batman": {
        "patterns": ["batman", "batmobile", "gotham", "joker", "robin",
                      "batgirl", "bruce wayne", "dark knight"],
        "tags": ["batman", "dc", "superhero", "comics"]
    },
    "marvel": {
        "patterns": ["marvel", "spider-man", "spiderman", "x-men", "xmen",
                      "wolverine", "hulk", "iron man", "captain america",
                      "avengers", "thor"],
        "tags": ["marvel", "superhero", "comics"]
    },
    "disney": {
        "patterns": ["disney", "mickey", "minnie", "donald duck", "goofy",
                      "pluto", "bambi", "dumbo", "aladdin", "lion king",
                      "ariel", "cinderella"],
        "tags": ["disney", "cartoon", "animation"]
    },
    "apple_hw": {
        "patterns": ["imac", "ibook", "powerbook", "power mac", "powermac",
                      "macintosh", "mac ii", "mac se", "quadra", "centris",
                      "performa", "g3", "g4", "power pc", "powerpc", "newton",
                      "emac", "cube"],
        "tags": ["apple", "mac", "hardware"]
    },
    "beos": {
        "patterns": ["bebox", "beos", "be box", "be os"],
        "tags": ["beos", "retro", "hardware"]
    },
    "looneytunes": {
        "patterns": ["looney tunes", "bugs bunny", "daffy duck", "tweety",
                      "sylvester", "tasmanian devil", "road runner", "wile e"],
        "tags": ["looneytunes", "warnerbros", "cartoon"]
    },
    "drseuss": {
        "patterns": ["dr. seuss", "dr seuss", "cat in the hat", "grinch",
                      "lorax", "horton", "sam-i-am"],
        "tags": ["drseuss", "children", "illustration"]
    },
    "monster": {
        "patterns": ["dracula", "frankenstein", "mummy", "werewolf", "wolfman",
                      "nosferatu", "phantom", "zombie", "vampire", "grim reaper",
                      "invisible man", "creature from", "lagoon creature"],
        "tags": ["monster", "horror", "halloween"]
    },
    "southpark": {
        "patterns": ["south park", "southpark", "cartman", "kenny", "kyle",
                      "stan marsh"],
        "tags": ["southpark", "cartoon", "tv"]
    },
    "futurama": {
        "patterns": ["futurama", "fry", "bender", "leela", "zoidberg",
                      "professor farnsworth"],
        "tags": ["futurama", "cartoon", "scifi"]
    },
    "tmnt": {
        "patterns": ["ninja turtle", "tmnt", "leonardo", "donatello",
                      "raphael", "michelangelo", "splinter", "shredder"],
        "tags": ["tmnt", "cartoon", "superhero"]
    },
    "japanese_food": {
        "patterns": ["sushi", "ramen", "onigiri", "mochi", "tempura",
                      "udon", "soba", "takoyaki", "yakitori", "bento",
                      "wagashi", "dango", "manjuh", "anman", "okashi",
                      "osechi", "katsu", "tonkatsu"],
        "tags": ["japanese", "food"]
    },
}


def apply_keyword_rules(tags_data):
    """Apply keyword rules as a safety net. Additive only — never removes tags."""
    applied = 0
    for icon in tags_data['icons']:
        # Build a searchable text from name, description, collection
        search_text = ' '.join([
            icon.get('display_name', ''),
            icon.get('description', ''),
            icon.get('collection', ''),
            icon.get('file', ''),
        ]).lower()

        existing_themes = set(icon.get('themes', []))

        for rule_name, rule in KEYWORD_RULES.items():
            # Check if any pattern matches
            if any(p in search_text for p in rule['patterns']):
                new_tags = set(rule['tags']) - existing_themes
                if new_tags:
                    icon['themes'] = sorted(existing_themes | new_tags)
                    existing_themes = set(icon['themes'])
                    applied += len(new_tags)

    return applied


def main():
    test_mode = None
    resume_mode = "--resume" in sys.argv
    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        test_mode = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 10
        print(f"TEST MODE: Processing only {test_mode} icons")

    print("Theme Validator & Enricher - All Icons")
    print("=" * 50)

    client = anthropic.Anthropic()
    tags = load_tags()

    # Load progress for resume
    progress = load_progress() if resume_mode else {"completed_batches": set()}
    if isinstance(progress.get("completed_batches"), list):
        progress["completed_batches"] = set(progress["completed_batches"])

    all_indices = list(range(len(tags['icons'])))

    if test_mode:
        all_indices = all_indices[:test_mode]

    print(f"Total icons: {len(tags['icons'])}")
    print(f"To process: {len(all_indices)}")
    print(f"Batch size: {BATCH_SIZE}, Workers: {WORKERS}")

    # Build all batch index lists
    all_batches = []
    for i in range(0, len(all_indices), BATCH_SIZE):
        all_batches.append(all_indices[i:i + BATCH_SIZE])

    total_batches = len(all_batches)

    # Filter out already-completed batches in resume mode
    pending_batches = []
    for batch_num, batch_indices in enumerate(all_batches):
        if batch_num not in progress["completed_batches"]:
            pending_batches.append((batch_num, batch_indices))

    if resume_mode and len(pending_batches) < total_batches:
        print(f"Resuming: {total_batches - len(pending_batches)} batches already done, "
              f"{len(pending_batches)} remaining")

    if not pending_batches:
        print("All batches already completed!")
        print("\nApplying keyword safety net...")
        added = apply_keyword_rules(tags)
        print(f"  Added {added} tags from keyword rules")
        save_tags(tags)
        return

    retagged = 0
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time()
    completed_in_session = 0
    save_every = 5

    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {}
            for batch_num, batch_indices in pending_batches:
                future = executor.submit(
                    process_batch, client, tags, batch_indices,
                    batch_num + 1, total_batches
                )
                futures[future] = batch_num

            for future in as_completed(futures):
                batch_num = futures[future]
                result = future.result()
                completed_in_session += 1

                if result:
                    count, inp, out = result
                    retagged += count
                    total_input_tokens += inp
                    total_output_tokens += out

                    with save_lock:
                        progress["completed_batches"].add(batch_num)

                total_done = len(progress["completed_batches"])
                elapsed = time() - start_time
                rate = retagged / elapsed if elapsed > 0 else 0
                remaining = len(all_indices) - total_done * BATCH_SIZE
                eta = remaining / rate if rate > 0 else 0
                cost = (total_input_tokens * 3 + total_output_tokens * 15) / 1_000_000

                print(f"\r  Batch {total_done}/{total_batches} | "
                      f"{retagged} retagged | "
                      f"{rate:.0f} icons/s | "
                      f"ETA {eta/60:.0f}m | "
                      f"${cost:.2f}",
                      end="", flush=True)

                if completed_in_session % save_every == 0:
                    with save_lock:
                        save_tags(tags)
                        save_progress(progress)

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving progress...")
        save_tags(tags)
        save_progress(progress)
        print(f"Saved. {len(progress['completed_batches'])}/{total_batches} batches complete.")
        print("Run with --resume to continue.")
        sys.exit(0)

    # Final save
    save_tags(tags)
    save_progress(progress)

    elapsed = time() - start_time
    total_cost = (total_input_tokens * 3 + total_output_tokens * 15) / 1_000_000

    print()
    print()
    print(f"API pass complete! Retagged {retagged} icons in {elapsed:.0f}s.")
    print(f"Tokens: {total_input_tokens:,} input, {total_output_tokens:,} output")
    print(f"Cost: ${total_cost:.2f}")

    # Post-enrichment keyword safety net
    print()
    print("Applying keyword safety net...")
    added = apply_keyword_rules(tags)
    print(f"  Added {added} tags from keyword rules")
    save_tags(tags)

    # Stats
    print()
    print("Final stats:")
    theme_counts = [len(icon.get('themes', [])) for icon in tags['icons']]
    print(f"  Avg themes per icon: {sum(theme_counts)/len(theme_counts):.1f}")
    print(f"  Icons with <=3 themes: {sum(1 for c in theme_counts if c <= 3)}")
    print(f"  Icons with >=5 themes: {sum(1 for c in theme_counts if c >= 5)}")
    vibe_count = sum(1 for icon in tags['icons'] if icon.get('vibes'))
    print(f"  Icons with vibes: {vibe_count}")

    # Clean up progress file
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
    print("\nDone!")


if __name__ == "__main__":
    main()
