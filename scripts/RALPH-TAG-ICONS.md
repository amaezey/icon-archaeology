# Ralph Loop: Tag Icons

## Task
Analyze and tag classic Mac icons from `/Users/mae/Documents/Inspo space/public/icons/extracted-transparent/` and save results to `tags.json`.

## CRITICAL: Image Limit
**Claude API has a 100 image limit per context. Read ONLY 10 icons per iteration. No exceptions.**

## Each Iteration (ONE batch only, then exit)

1. **Read `tags.json`** to get the `tagged_files` array
2. **List files** and find the NEXT 10 untagged icons only
3. **Read exactly 10 images** - NO MORE
4. **Tag each** with:
   - `primary`: food|character|animal|folder|hardware|ui|object|vehicle|nature|symbol|text
   - `secondary`: array of 0-3 tags (cute, retro, holiday, gaming, japanese, portrait, scifi, fantasy, horror, music, art, sports, kitchen, office, science, military, fashion)
   - `colors`: 1-2 dominant colors
   - `vibe`: one word (playful, technical, spooky, cozy, elegant, quirky, minimal, retro)
5. **Update tags.json** - add to `tagged_files`, append to `icons`, update count
6. **Report**: "Tagged X/15097 icons (+10 this iteration)"
7. **STOP** - let the next iteration continue

Do NOT process multiple batches in one iteration. One batch of 10, then stop.

## Completion

When `tags.json` shows all 15097 icons tagged:
```
<promise>TAGGING COMPLETE</promise>
```

## Files
- Input: `/Users/mae/Documents/Inspo space/public/icons/extracted-transparent/*.png`
- Output: `/Users/mae/Documents/icon-archaeology/tags.json`
