# PDF Book Conversion

Convert single-column, English-language, text-based PDF books into readable EPUBs while preserving their content.

## Language

**Source book**: An English-language, single-column PDF with extractable text; scanned PDFs and complex multi-column layouts are outside the initial scope.

**Book profile**: Optional per-book configuration describing layout exceptions that automatic detection cannot resolve.

**Converted book**: A reflowable EPUB preserving the source book's prose, headings, notes, tables, and figures.

## Relationships

- A **Source book** produces a **Converted book**.
- A **Source book** may have one **Book profile**.

## Example dialogue

> **Developer:** Does every source book need a book profile?
> **User:** No. Detect the layout automatically and use a profile for exceptions.

## Review outcomes

**Failed conversion**: A conversion with unresolved layout or validation problems that produces diagnostics and configuration artifacts, but no EPUB.

**Review report**: A list of affected pages and layout issues requiring book-profile overrides.

- A **Failed conversion** produces a **Review report** and no **Converted book**.

**Content accounting**: Classification of every extracted content line as prose, a footnote, a preserved image, or an explicit exclusion.

**Automated validation**: Checks of content accounting and internal links, distinct from human review of visual appearance.

**Print artifact**: A running header, repeated footer, page number, or printer’s mark associated with pagination rather than substantive book content.

## Preservation rules

- Preserve substantive prose and footnotes; exclusions are limited to **Print artifacts** and duplicate text.
- Preserve tables and diagrams as complete high-resolution images.
- An unreconstructable page causes a **Failed conversion**; full-page image fallback is not allowed.
- A **Failed conversion** leaves any previously generated **Converted book** unchanged.

# Codex Conversation Timeline

Inspect the recorded actions in a Codex conversation over time.

## Language

**Conversation flame chart**: A chronological view with real time horizontally, nested actions vertically, separate lanes for parallel calls, and timestamped markers for prompt submissions.

**Agent lane**: A horizontal band of actions belonging to the main agent or one of its recursively included subagents, with subagent lanes below the main agent on a shared time axis.

**Recorded action**: An activity visible in Codex's records, including prompts, assistant messages, reasoning intervals, tool calls, commands, approvals, and subagent lifecycle events.

**Conversation snapshot**: A fixed view of the linked conversation and its descendant agents based on the records available when captured.

## Interpretation rules

- Show all recorded action categories by default, with filters to hide categories.
- Show missing or uncertain timing explicitly; never invent durations.
- Include nested calls and command steps only when separately recorded by Codex.
- Identical source data produces identical output; rerunning captures new activity.
- Present the snapshot as a self-contained interactive HTML file with zoom, pan, and action details on click.
- Show elapsed time from the first event on the axis and absolute UTC timestamps in tooltips and details.
- Nest actions only when recorded relationships establish parentage; put overlapping actions in separate rows otherwise.
- Action details include recorded timestamps, duration, status, name or command, arguments, and output, with long content expandable.
- Missing descendant records or malformed logs produce a partial snapshot with a visible notice of omissions; an unreadable or missing requested conversation prevents generation.
- Unfinished actions appear at their recorded start with an in-progress or completion-unknown status, without an invented end time or duration.

## Example dialogue

> **Developer:** Should repeated calls be aggregated?
> **User:** No; preserve their ordering, gaps, and overlap.
