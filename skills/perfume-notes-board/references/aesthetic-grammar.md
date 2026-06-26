# Aesthetic Grammar

Use this reference whenever creating a perfume notes board for Patrick.

## Core Doctrine

Render the verb, not the noun.

Do not render "luxury," "dark academia," "sprezzatura," "adventure," or "masculinity" as static states. Select items that show operations still in motion:

- earning
- holding tension
- operating on a live problem
- hosting or setting a field
- competing under pressure
- preparing privately before public entry
- simplifying ruthlessly
- surviving contact with reality

Every item should answer at least one question:

- What is this doing?
- What did it earn?
- What pressure does it survive?
- What field does it prepare, enter, or control?

## Source Priority

When the user provides a list of Pinterest board names, those named boards are the source corpus. Search is a fallback, not a peer.

Assume this runs inside Codex with the in-app browser open and signed in. Keep Pinterest access read-only. Do not edit boards or interact with account-mutating controls.

Use this priority order:

1. Pins from the supplied Pinterest boards.
2. Other user-supplied images or screenshots.
3. Pinterest search results, only when the supplied boards cannot support the needed note or the user explicitly requests expansion.

Do not use general web search, stock imagery, AI-generated objects, or plausible substitutes by default.

Do not browse the user's broader Pinterest profile or other boards unless the user explicitly names them for this task. If a board name is ambiguous or unavailable, ask for clarification rather than exploring other boards.

When choosing between an exact search result and a slightly less exact board pin, prefer the board pin unless the search result carries a note the board truly cannot express. If a search-sourced item survives the audit, disclose that it is search-sourced in the proseboard.

Keep source provenance with each candidate image: board name, pin URL when available, local image path, and whether the image came from a named board, user upload, or search.

## Row Logic

`Top Notes` are the first hit: immediate sensory charge, first-read persona, opening temperature.

Good top notes are not vague moods. They are first-contact signals with an active edge: black leather as tool, Mediterranean leisure with danger awake, scent ritual before field-entry, polish with a pulse.

`Middle Notes` are the operating field: where the aesthetic proves itself socially, strategically, erotically, intellectually, or competitively.

Good middle notes show pressure and conduct: Eddie Halstead under jungle rules, Roland-Garros clay, martini-hour manners, hospitality as scene control, legal or strategic gamesmanship.

`Base Notes` are the durable substrate: tools, rooms, machines, training, and objects that keep the whole thing from becoming cosplay.

Good base notes make the romance accountable to use: Defender, E-Type, NATO strap, private study, watch roll, field kit, workbench, margin-noted book, room as instrument.

## Patrick-Specific Attractors

Use these as taste anchors, not mandatory checklist items:

- feral and refined held in live tension
- provenance over logos
- earned history over price signaling
- luxury as tool quality
- luxury as romance/leisure with Jess
- luxury as capital-conversion infrastructure
- luxury as ability to bend the world toward a desired scene
- Mediterranean sensuality and leisure
- scholarly competence that can leave the library and survive the field
- rugged adventure as earned patina
- legal/strategic gamesmanship
- polished aggression
- night weapon / erotic arrogance / black-leather NYC charge
- Gentry and Elite reconciled: aristocratic inheritance forced to survive jungle rules
- grace under competitive pressure
- earned body / physical competence
- aristocratic sport as social field
- winning as proof of reality-contact
- solitude and risk in mountain environments
- machine as extension of competence
- old-money leisure with mechanical stakes
- sensual memory and scene-setting through scent
- private ritual before public field-entry
- rooms as field-setting instruments
- hosting as capital conversion
- private study / ritual chamber
- sensual but controlled indulgence
- hospitality as scene control
- earned competence
- positive-sum default
- reality-contact
- restraint
- risk with competence attached
- contrast that makes warmth and luxury sharper
- danger held under discipline
- states of matter under use

## Near-Miss Refusals

Refuse the near-miss before it seduces the board.

`Generic quiet luxury / stealth wealth` is wrong when it removes logos but keeps the point as wealth-signaling. The right move is not "expensive and discreet"; it is a specific earned history. If the item cannot name what it earned from, it is probably just a price tag.

`Menswear-blog sprezzatura` is wrong when it performs ease. The right move is structural tension between feral and refined: the garment or object could fall either way and does not. Avoid studied carelessness.

`Instagram dark academia` is wrong when books, tweed, and candlelight become props. The right move is intellectual atmosphere as a mind actively operating on a live problem: margin notes, frameworks mid-use, a belief under attack.

`Cosplay masculinity` is wrong when Bond, Bourne, Eddie, Harvey, or similar figures are treated as costumes. They only work when used for a specific operation:

- Bond: blunt instrument under polish.
- Bourne: ruthless simplifier; aesthetics as tool.
- Eddie Halstead: Gentry and Elite reconciled under jungle pressure.
- Harvey-style figures: legal/strategic gamesmanship and polished aggression.
- Black-leather figures: night weapon charge, not "cool jacket guy."

## Naming Rules

Use proper nouns when the source supports them:

- `Jason Bourne`
- `Dickie Greenleaf`
- `Eddie Halstead`
- `Cartier Panthere`
- `Land Rover Defender`
- `Jaguar E-Type`
- `Roland-Garros Clay`
- `Byredo Bibliotheque`
- `Diptyque Eau Duelle`
- `Diptyque Do Son`

Use precise canonical nouns when the source supports the thing but not a specific proper noun:

- `The Dressing Tray`
- `Mediterranean Terrace`
- `Martini Hour`
- `The Private Study`
- `The Watch Roll`
- `The Field Kit`

Avoid vague labels:

- chapter marker watch
- field-entry tool
- controlled sensuality object
- luxury signal
- dark academia mood
- masculine energy

Do not hallucinate specificity. Do not label a generic martini image `Temple Bar` unless the source actually supports Temple Bar.

## Visual Style

Imitate the plain reference-board grammar:

- opaque white background
- black text
- bold plain sans headings
- simple title near the top
- large section headings
- images arranged in clean rows
- labels/captions directly below each image
- no decorative gradients, beige editorial deck styling, serif magazine typography, cards, shadows, or collage clutter

Use a practical font stack: Helvetica Neue, Helvetica, Arial, SF Pro, or another plain grotesk/sans fallback.

## Selection Audit

Before assembling the image, check:

- Are there exactly 12 items unless the user requested a smaller board?
- Are the rows literally Top Notes, Middle Notes, Base Notes?
- Does each row do different work?
- Does every item answer a doctrine question?
- Are any labels unsupported by their image?
- Are there repeated items, repeated functions, or repeated aesthetics?
- Is any choice a generated/source-less stand-in?
- Is any choice search-sourced when a board-sourced item could do the work?
- Is source provenance known for every final image?
- Is any choice merely a state instead of an operation?
- Is any choice cosplay?
- Is any caption abstract where a concrete proper or canonical noun would work?

Revise once automatically before rendering.
