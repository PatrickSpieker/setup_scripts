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
