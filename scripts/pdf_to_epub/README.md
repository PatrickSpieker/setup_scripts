# PDF to EPUB

macOS, Calibre in `/Applications`, and Homebrew Python 3.12 are required. Install once with `scripts/install-pdf-to-epub.sh` (also invoked by `setup.sh`). Installation downloads hash-locked dependencies into `~/.local/share/pdf-to-epub/venv`. Conversion is local and offline.

```sh
pdf-to-epub inspect book.pdf
pdf-to-epub convert book.pdf --output book.epub --profile book.yaml
```

Inspection writes `book.effective.yaml` and `book.report.html`. Review the self-contained report and save an edited profile before converting. `--output` on inspection changes artifact placement. Conversion writes the same artifacts beside the requested EPUB. Generated files overwrite automatically; there is no force flag. Input PDF/profile aliases are rejected. A failing conversion preserves any existing EPUB and emits no draft.

Only English, single-column PDFs with real text layers are supported. Scans, unresolved layouts, unaccounted content, uncertain word joins, broken notes, and invalid EPUBs fail. There is no OCR or full-page-image fallback. Tables/diagrams use whole image crops; body prose remains reflowable. Automatic checks cannot certify visual quality.

## Profile version 1

Unknown keys and duplicate YAML keys fail. Omitted fields use inspection defaults. `profiles/danish-industrial-foundations.yaml` documents the original book's layout. All page numbers are one-based PDF pages, not printed page numbers. Boxes are `[left, top, right, bottom]` in PDF points. The report lists stable `p0001-l0001` source line IDs.

| Field | Meaning |
|---|---|
| `version` | Required supported version: `1` |
| `source_sha256` | Optional source fingerprint; effective profiles always record it. Clear when adapting to a different PDF. |
| `metadata` | `title`, `author`, `publisher`, `language: en` |
| `layout` | `top`, `bottom`, `body_font`, `body_size`, `left`, `right`, `indent`, `line_height`. Null values are inferred. |
| `headings` | `font`, `h1_size`, `h2_size`, `chapter_pattern` |
| `notes` | `font` prefix and exact `size`; numbered footnotes restart per chapter |
| `pages` | Mapping of page numbers to `role`, optional `top`/`bottom`. Roles: `body`, `frontmatter`, `references`, `contents`, `jacket`, `duplicate`. Duplicate pages require `duplicate_of`; text must verify against a retained page. Jackets have `panels: [{title: …, box: […]}]`. |
| `illustrations` | List of `{page, box, rotate, caption, retain_text}`. Rotation is clockwise 0/90/180/270. `retain_text` names source lines overlapping a graphic that must also remain reflowable. |
| `duplicates` | List of `{line: ID, of: [IDs]}`. Exclusion requires matching retained text. |
| `artifacts` | List of `{line: ID, kind: page_number\|printer_mark}`; recognized patterns are verified. |
| `line_overrides` | Mapping of IDs to `paragraph`, `continue`, `heading1`, `heading2`, or `note` |
| `hyphenation` | `keep`/`join` lists of case-sensitive split words, e.g. `foun-dation`. Ambiguous joins fail instead of guessing. |
| `cover` | Optional `{page, box}` for the cover panel |
| `render_dpi` | Illustration resolution, 144–600; default 240 |

Margins alone never authorize dropping text. Running matter requires repeated margin text; explicit exclusions require evidence. Reports expose each source line's destination, exclusions, unresolved issues, normalized joins, and dependency versions.

Packaging uses a fresh Calibre configuration, no user plugins, and structural validation. EPUB identifiers, dates, ZIP metadata and entry order are normalized. With the same input bytes, effective profile, and dependency/toolchain versions, output bytes must match. Updating Calibre, Python, or dependencies can change output; retain the report alongside a reusable profile.
