---
name: pdf-to-epub-md
description: Convert every PDF in the current directory to EPUB-bound markdown via pdftotext, then dispatch one `epub-md-formatter` agent per book in parallel to clean each output.
---

# PDF to EPUB Markdown

Convert every PDF in the current directory into Calibre-ready markdown. `pdftotext -layout` does the raw text extraction (seconds per book, no ML, no GPU). One `epub-md-formatter` subagent per PDF reformats each output in parallel.

## When to use

- Directory of PDF books, want markdown ready for Calibre/Pandoc → EPUB.
- User explicitly asks to "extract these PDFs," "make EPUBs from these," or similar.

Do NOT use for:
- Single-file conversions where the user just wants raw text — `pdftotext` directly is simpler.
- Non-book PDFs (forms, invoices, receipts).
- Scanned PDFs without a text layer — pdftotext returns empty/garbage. The skill flags these and the user handles them separately (Tesseract, Adobe OCR, paid OCR service).

## Steps

### 1. Pre-flight checks

Requires `pdftotext` and `pdfinfo` from poppler-utils.

```bash
if ! command -v pdftotext >/dev/null || ! command -v pdfinfo >/dev/null; then
  echo "Error: poppler-utils not installed. Run: brew install poppler"
  exit 1
fi

if [[ -e outputs ]]; then
  echo "Error: 'outputs' already exists in $(pwd). Move or remove it before running."
  exit 1
fi

shopt -s nullglob
pdfs=( *.pdf )
shopt -u nullglob
if (( ${#pdfs[@]} == 0 )); then
  echo "Error: no PDFs in $(pwd)."
  exit 1
fi
echo "Found ${#pdfs[@]} PDF(s)."
mkdir outputs
```

### 2. Extract with pdftotext

`-layout` preserves columns and indentation — the formatter agent needs this to reconstruct chapter and section structure.

```bash
extracted=()
needs_ocr=()

for pdf in "${pdfs[@]}"; do
  stem="${pdf%.pdf}"
  mkdir -p "outputs/$stem"
  pdftotext -layout "$pdf" "outputs/$stem/$stem.md" 2>/dev/null || true

  pages=$(pdfinfo "$pdf" 2>/dev/null | awk '/^Pages:/ {print $2}')
  pages=${pages:-1}
  words=0
  [[ -f "outputs/$stem/$stem.md" ]] && words=$(wc -w < "outputs/$stem/$stem.md" | tr -d ' ')
  ratio=$(( words / pages ))

  if (( ratio < 30 )); then
    needs_ocr+=("$pdf ($words words / $pages pages)")
    rm -rf "outputs/$stem"
    echo "  SKIPPED (likely scanned, needs OCR): $pdf"
  else
    extracted+=("$pdf")
    echo "  extracted: $pdf ($words words / $pages pages)"
  fi
done

echo
echo "Extracted ${#extracted[@]} PDF(s)."
if (( ${#needs_ocr[@]} > 0 )); then
  echo "Skipped ${#needs_ocr[@]} (no text layer — handle separately):"
  printf '  %s\n' "${needs_ocr[@]}"
fi
```

The 30-words-per-page threshold is the heuristic for "is there a real text layer." Books with sparse pages (lots of figures) still clear it; truly scanned PDFs return near-zero words and get flagged.

### 3. Dispatch formatter agents — in parallel

For each surviving `outputs/<stem>/<stem>.md`, spawn an `epub-md-formatter` agent. **Send all agent calls in a single message** so they run in parallel — books are independent.

Each agent prompt should be self-contained. Template:

```
Reformat outputs/<stem>/<stem>.md into EPUB-bound markdown per the rules in your system prompt.

Source: `pdftotext -layout` extraction of <stem>.pdf.
File to edit: outputs/<stem>/<stem>.md (edit in place).

Note: pdftotext output has NO markdown structure — it's plain text with form-feed (\f) characters between pages and column-preserved indentation. Your job is the full structural reconstruction:
- Detect chapter / section / subsection hierarchy and add markdown headings.
- Drop running headers, footers, page numbers.
- Rejoin paragraphs broken across page boundaries.
- Preserve italic/bold cues if recoverable from indentation or punctuation patterns; flag anything ambiguous.

Working procedure:
1. Read the file end-to-end. Note chapter structure, presence of Parts, footnote style, anything obviously broken.
2. Plan the heading hierarchy before editing.
3. Edit in place. Many small edits, not one giant rewrite.
4. Run the verification checklist from your system prompt.
5. Report what you changed and any concerns the user should review by hand.
```

Use the `Agent` tool with `subagent_type: "epub-md-formatter"`.

If there are many PDFs (more than ~8) and dispatching them all at once would saturate the system, batch in groups; otherwise one parallel volley is fine.

### 4. Final report

After all agents return, summarize for the user:

- N PDFs extracted; N skipped for OCR; N formatter agents run.
- Per-book output paths.
- Any books the formatter flagged for human review (heading ambiguity, suspicious page-break joins, lost emphasis).
- The list of skipped (no-text-layer) PDFs the user must OCR separately.

Do **not** commit, push, or move files. The user owns next steps.

## Notes

- `pdftotext -layout` drops embedded images. For books where figures matter, run `pdfimages -all <pdf> outputs/<stem>/img` as a separate manual pass and reference them in the markdown by hand. Most personal-library use cases don't need this.
- The skill is intentionally text-only. Earlier versions used `marker` (3.2GB of ML models, ~15-25 min/book on CPU/MPS). For a real book directory the time/value tradeoff was bad: most book PDFs already have a usable text layer, and marker's heading output still required `epub-md-formatter` cleanup. Removing marker cut wall time from hours to seconds.
- The "needs OCR" path is genuinely manual. Tools to consider when a PDF gets flagged: `ocrmypdf` (wraps Tesseract, runs locally, free), Adobe Acrobat's built-in OCR, or a paid OCR API. Once OCR'd, re-run this skill on the resulting PDF.
- The skill never deletes files. Re-runs require deleting `outputs/` first.

### Formatter agent failure modes (observed at scale)

When dispatching `epub-md-formatter` agents on a real-library batch (~30 books), expect:

- **Rate limits** if you launch >5-8 Opus agents at once on books >100K words. The platform throttles individual agents with "Server is temporarily limiting requests" — that agent returns nothing and burns no useful work. Mitigation: batch in groups of 3-5; retries on a separate volley generally succeed.
- **Content-filter blocks** on ~20-25% of books, unpredictably. Manifests as `400 invalid_request_error: Output blocked by content filtering policy`. The filter fires when the model echoes certain source-text patterns into its output stream. *Critically, much of the agent's edit work often lands on disk before the filter blocks the final report* — so a "failed" agent may have substantially cleaned the file. After a failed batch, check `grep -c $'\f' outputs/<stem>/<stem>.md` and `grep -c '^## ' …` before retrying: if form-feeds are gone and h2 headings exist, the file is likely usable as-is.
- **Sonnet retries don't help** content-filtered books — the filter is at the API layer, not model-specific.
- **Giant books (>300K words / >700 pages)** — Marketing Economics, intermediate accounting textbooks, etc. — push past what one agent can reasonably process in one pass. Either skip the formatter for these (raw `pdftotext` output is acceptable for Calibre) or accept partial structural work.
- **Final fallback for un-processable files**: a small Python pass that strips form-feeds, drops standalone-digit page-number lines, and removes lines that repeat 5+ times (running headers). Won't add heading hierarchy but produces a Calibre-ingestible document. Reserve for the 1-2 books per batch where the agent failed entirely.
