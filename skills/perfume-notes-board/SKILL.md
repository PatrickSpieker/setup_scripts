---
name: perfume-notes-board
description: Create Patrick-style "me if I was a perfume" top/middle/base notes boards in Codex from a user-provided visual corpus, especially a list of Pinterest board names viewed through the signed-in Codex browser. Use when the user asks for a perfume notes board, top notes/middle notes/base notes collage, aesthetic notes board, or wants Codex to translate personal taste into both a defended proseboard and a final visual board. Prioritizes pins from explicitly named Pinterest boards over any search results, enforces board-native/user-supplied images by default, and renders 12 named items with literal Top Notes / Middle Notes / Base Notes rows, opaque white background, black readable sans text, and captions below each image.
---

# Perfume Notes Board

Create both:

1. A **proseboard**: the theory layer, defending each selected item.
2. A **visual board**: the final white-background notes-board image.

Always read `references/aesthetic-grammar.md` before selecting items or writing captions.

This skill is optimized for Codex. Assume the Codex in-app browser is available when Pinterest board names are supplied. If another agent surface loads this skill, use the same read-only source rules with equivalent browser/file tools; do not write instructions for external Pinterest automation.

## Non-Negotiables

- Use **board-native or user-supplied images only** by default. Do not generate source images, use web-search substitutions, or invent plausible stand-ins unless the user explicitly overrides this rule.
- Accept Pinterest **board names**, not URLs, as the normal input. When board names are supplied, assume the Codex browser is open and signed in.
- Treat only the explicitly named Pinterest boards as the primary ordered source corpus. Prefer pins from those boards over search results.
- Do not edit Pinterest boards: do not save pins, delete pins, move pins, rename boards, follow accounts, comment, like, or otherwise mutate the account.
- Do not read from boards the user did not name or otherwise grant access to for this task. If a board is ambiguous, private, inaccessible, or cannot be found, ask instead of exploring the profile.
- Produce the visual board by default after self-critiquing the proseboard. Pause only when the corpus cannot support the named item or the source set is too thin.
- Keep the section names literally: `Top Notes`, `Middle Notes`, `Base Notes`.
- Use 12 total items. Default to 4 items per section; use 3 per section only if the user explicitly asks for a smaller board.
- Use proper nouns when the source supports them. Otherwise use precise canonical nouns. Never use mushy labels like "chapter marker watch" or "controlled sensuality object."
- The visual style is a simple meme-board grammar: opaque white background, black readable sans text, bold section headings, item captions directly below images, no editorial magazine styling.

## Workflow

1. **Ingest the corpus**
   - Accept one or more Pinterest board names as an ordered source list, for example `Random Aesthetic Things` or `p inspo`.
   - Use the signed-in Codex in-app browser for Pinterest. Navigate to the named boards without requiring URLs.
   - Stay read-only. Scroll, inspect, screenshot, and download visible assets only; do not click controls that mutate Pinterest state.
   - Scroll enough to understand each board and capture a representative source set.
   - Save or screenshot board-native images into a local working folder.
   - Keep a source manifest with the board name, local image path, and pin URL when available.
   - Build a contact sheet when there are many candidate images.

2. **Apply source priority**
   - Tier 1: pins from the supplied Pinterest boards, in the user's supplied order when relevance is otherwise equal.
   - Tier 2: other user-supplied local images or screenshots.
   - Tier 3: Pinterest search results, only when the board corpus cannot support a needed note or the user explicitly asks for search expansion.
   - Do not use general web search, AI-generated images, stock stand-ins, or untraceable images by default.
   - Do not treat the user's broader Pinterest profile as a source. Named boards only.
   - If any Tier 3 item is used, disclose it in the proseboard and explain why no board-native image carried that note.

3. **Draft the proseboard**
   - Select candidates for `Top Notes`, `Middle Notes`, and `Base Notes`.
   - For each item, write a name and a short caption.
   - Every item must answer at least one doctrine question: what is it doing, what did it earn, what pressure does it survive?

4. **Self-critique once**
   - Audit for false specificity, repeats, cosplay, generated stand-ins, row-logic failure, weak nouns, unsupported proper nouns, and labels that describe states instead of operations.
   - Audit source priority: replace search-sourced items with board-sourced items unless the search result is materially better and the board lacks the note.
   - Revise the proseboard before making the visual.

5. **Assemble the visual board**
   - Use `scripts/assemble_notes_board.py` with a JSON spec containing title, sections, labels, captions, and source image paths.
   - Use only images already collected from the user's visual corpus.
   - Inspect the output image. Re-render if text is too small, overlaps, or the crop loses the object.

6. **Return both outputs**
   - In the final response, include the proseboard and the rendered image path.
   - Mention any weak proxies, unsupported names that were avoided, or lower-priority search sources used.

## Proseboard Format

Use concise prose, not a shopping list:

```markdown
**<Title>**

**Top Notes**
**<Named Item>**  
<caption/defense>

...

**Middle Notes**
...

**Base Notes**
...
```

## Visual Spec Format

Create a JSON file shaped like this and pass it to the assembler:

```json
{
  "title": "NYC Feral Patrick",
  "subtitle": "top notes / middle notes / base notes",
  "output": "outputs/nyc-feral-patrick.png",
  "sections": [
    {
      "name": "Top Notes",
      "items": [
        {
          "label": "Jason Bourne",
          "caption": "ruthless simplifier; black leather as tool",
          "image": "outputs/board-assets/P34.jpg",
          "source": {
            "tier": "board",
            "board": "P Inspo",
            "pin_url": "https://www.pinterest.com/pin/example/"
          },
          "focal": [0.5, 0.45]
        }
      ]
    }
  ]
}
```

The assembler validates the three section names, item counts, image paths, and text fit.

## Script

Run:

```bash
python3 scripts/assemble_notes_board.py path/to/spec.json
```

Useful options:

```bash
python3 scripts/assemble_notes_board.py path/to/spec.json --output outputs/final-board.png
python3 scripts/assemble_notes_board.py path/to/spec.json --width 1600
```

The script uses a Helvetica/Arial/SF-style sans stack and keeps the output plain: white background, black text, no borders, no decorative color system.
